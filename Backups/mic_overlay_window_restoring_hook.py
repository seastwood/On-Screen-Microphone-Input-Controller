import ctypes

from PyQt5.QtWidgets import QApplication, QLabel, QWidget, QDialog, QVBoxLayout, QSlider, QPushButton
from PyQt5.QtCore import Qt, QTimer, QPoint
from PyQt5.QtGui import QColor, QPainter, QPen
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
from comtypes import CLSCTX_ALL
import sys
import os
import sounddevice as sd
import numpy as np
from ctypes import windll
from ctypes.wintypes import HWND
GetForegroundWindow = windll.user32.GetForegroundWindow
SetForegroundWindow = windll.user32.SetForegroundWindow

# Define the base config directory in the user's local AppData
CONFIG_DIR = os.path.join(os.getenv("LOCALAPPDATA"), "MuteOverlay")

# Ensure the directory exists
os.makedirs(CONFIG_DIR, exist_ok=True)

# File paths for volume and size settings
VOLUME_FILE = os.path.join(CONFIG_DIR, "volume_setting.txt")
SIZE_FILE = os.path.join(CONFIG_DIR, "size_setting.txt")
POSITION_FILE = os.path.join(CONFIG_DIR, "position_setting.txt")


# # File paths for volume and size settings
# VOLUME_FILE = "volume_setting.txt"
# SIZE_FILE = "size_setting.txt"
# POSITION_FILE = "position_setting.txt"

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Overlay Settings")

        # Get the screen's width and height
        screen_geometry = QApplication.desktop().availableGeometry()
        screen_center = screen_geometry.center()

        # Set the window's size
        width, height = 300, 250

        # Calculate the position to center the window
        x = screen_center.x() - width // 2
        y = screen_center.y() - height // 2

        # Set the geometry to position it at the center of the screen
        self.setGeometry(x, y, width, height)

        # Dark mode background and widget style
        self.setStyleSheet("""
            background-color: #2E2E2E;
            color: white;
            font-size: 18px;
        """)

        self.layout = QVBoxLayout(self)

        # Volume label and slider setup
        self.layout.addWidget(QLabel("On Volume"))
        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(parent.load_volume() if parent else 50)  # Default to 50 if parent is None
        self.volume_slider.setStyleSheet("""
                    QSlider::groove:horizontal {
                        background: #444444;
                        height: 14px;
                        border-radius: 4px;
                    }
                    QSlider::handle:horizontal {
                        background: #888888;
                        border-radius: 4px;
                        width: 20px;
                        height: 20px;
                    }
                """)
        self.layout.addWidget(self.volume_slider)

        # Size label and slider setup
        self.layout.addWidget(QLabel("Size"))
        self.size_slider = QSlider(Qt.Horizontal)
        self.size_slider.setRange(50, 400)
        self.size_slider.setValue(parent.load_size() if parent else 150)  # Default to 150 if parent is None
        self.size_slider.setStyleSheet("""
                    QSlider::groove:horizontal {
                        background: #444444;
                        height: 14px;
                        border-radius: 4px;
                    }
                    QSlider::handle:horizontal {
                        background: #888888;
                        border-radius: 4px;
                        width: 20px;
                        height: 20px;
                    }
                """)
        self.layout.addWidget(self.size_slider)

        # Apply Button
        self.apply_button = QPushButton("Apply")
        self.apply_button.setStyleSheet("""
            QPushButton {
                background-color: #5A5A5A;
                border: none;
                border-radius: 10px;
                padding: 10px;
            }
            QPushButton:hover {
                background-color: #808080;
            }
        """)
        self.layout.addWidget(self.apply_button)

        # Quit Button
        self.quit_button = QPushButton("Quit")
        self.quit_button.setStyleSheet("""
            QPushButton {
                background-color: #E74C3C;
                border: none;
                border-radius: 10px;
                padding: 10px;
            }
            QPushButton:hover {
                background-color: #C0392B;
            }
        """)
        self.layout.addWidget(self.quit_button)

        self.apply_button.clicked.connect(self.apply_settings)
        self.quit_button.clicked.connect(self.quit_application)

    def apply_settings(self):
        self.parent().set_volume(self.volume_slider.value())
        self.parent().set_size(self.size_slider.value())
        self.close()

    def quit_application(self):
        # Close the dialog and end the program
        QApplication.quit()


class MuteOverlay(QWidget):
    def __init__(self):
        super().__init__()
        self.live_amplitude = 0  # Store current audio amplitude
        self.stream = None  # Audio stream reference

        # Start the audio stream
        self.start_audio_stream()

        # Load the saved size and set the overlay geometry accordingly
        overlay_size = self.load_size()
        overlay_position = self.load_position()
        self.setGeometry(overlay_position.x(), overlay_position.y(), overlay_size, overlay_size)

        # Window setup - crucial flags
        self.setWindowFlags(
            Qt.WindowStaysOnTopHint |
            Qt.FramelessWindowHint |
            Qt.Tool |
            Qt.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)

        # Focus tracking setup
        self.last_focus_window = None
        self.setup_focus_tracking()

        self.label = QLabel("", self)

        # Set up the timer to periodically check mute status
        self.timer = QTimer()
        self.timer.timeout.connect(self.check_mute)
        self.timer.start(500)  # Check the mute status every 500ms

        # Initialize volume and mute state
        self.volume_percentage = self.load_volume()  # Initialize volume from file or default to 0
        self.muted = False
        self.is_dragging = False  # Flag for dragging
        self.drag_position = QPoint(0, 0)  # Starting position of drag
        self.show()

    def win_event_callback(self, hWinEventHook, event, hwnd, idObject, idChild, dwEventThread, dwmsEventTime):
        """Handle focus change events"""
        if hwnd and hwnd != self.winId():
            self.last_focus_window = hwnd
            # Debug print
            buffer = ctypes.create_unicode_buffer(255)
            self.user32.GetWindowTextW(hwnd, buffer, 255)
            print(f"Focus changed to: {hwnd} - '{buffer.value}'")

    def setup_focus_tracking(self):
        """Initialize Windows event hook for focus tracking"""
        self.user32 = windll.user32
        self.ole32 = windll.ole32

        # Initialize COM
        self.ole32.CoInitialize(0)

        # Define callback function type
        WinEventProc = ctypes.WINFUNCTYPE(
            None,
            ctypes.wintypes.HANDLE,
            ctypes.wintypes.DWORD,
            ctypes.wintypes.HWND,
            ctypes.wintypes.LONG,
            ctypes.wintypes.LONG,
            ctypes.wintypes.DWORD,
            ctypes.wintypes.DWORD
        )

        # Store callback reference
        self.win_event_proc = WinEventProc(self.win_event_callback)

        # Set up the hook
        self.hook = self.user32.SetWinEventHook(
            0x8005,  # EVENT_OBJECT_FOCUS
            0x8005,  # EVENT_OBJECT_FOCUS
            0,
            self.win_event_proc,
            0,
            0,
            0x0000 | 0x0002  # WINEVENT_OUTOFCONTEXT | WINEVENT_SKIPOWNPROCESS
        )

        if not self.hook:
            print("Failed to set event hook!")

    # def update_focused_window(self):
    #     """Continuously track the currently focused window"""
    #     current_window = GetForegroundWindow()
    #     if current_window and current_window != self.winId():
    #         self.last_focus_window = current_window
    #         # Debug print
    #         buffer = ctypes.create_unicode_buffer(255)
    #         windll.user32.GetWindowTextW(current_window, buffer, 255)
    #         print(f"Tracking window: {current_window} - '{buffer.value}'")

    def start_audio_stream(self):
        def callback(indata, frames, time, status):
            # Calculate the amplitude (volume) of the audio stream
            if hasattr(self, 'live_amplitude'):  # Check if attribute exists
                volume_norm = np.linalg.norm(indata)  # Euclidean norm = amplitude
                self.live_amplitude = min(volume_norm * 10, 1.0)  # Scale to [0.0 - 1.0]
                self.update()  # Trigger a repaint to update the visual effect

        try:
            # Start the audio stream with a callback to update amplitude
            self.stream = sd.InputStream(callback=callback, channels=1, samplerate=1000)
            self.stream.start()
        except Exception as e:
            print(f"Error starting audio stream: {e}")

    def check_mute(self):
        # Get the default audio device (microphone)
        devices = AudioUtilities.GetMicrophone()
        if not devices:
            self.label.setText("Mic: Not Found")
            return

        # Get interface to the microphone device and its volume control
        interface = devices.Activate(
            IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        volume = interface.QueryInterface(IAudioEndpointVolume)

        # Get the mute status and the volume level
        current_volume = volume.GetMasterVolumeLevelScalar()  # Value between 0.0 and 1.0
        is_muted = volume.GetMute() or current_volume == 0.0  # Treat volume 0 as muted too

        # Set volume as percentage
        self.volume_percentage = int(current_volume * 100)

        if is_muted != self.muted:
            self.muted = is_muted
            print(f"Mute status changed: {'Muted' if self.muted else 'Unmuted'}")
            self.update()

    def paintEvent(self, event):
        # Draw the main circle indicating mic volume
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Circle parameters
        radius = self.width() // 2 - 20  # Adjust radius based on window size
        center = self.rect().center()

        # Set color based on mute status
        if self.muted:
            color = QColor(255, 0, 0)  # Red when muted
        else:
            color = QColor(0, 255, 0, 128)  # Semi-transparent green when unmuted

            # Use live_amplitude for the visual effect
            max_pulse_radius = radius // 4  # Adjust this to control the pulse size
            pulse_radius = int(self.live_amplitude * max_pulse_radius)

            green = QColor(0, 255, 0, 60)  # Semi-transparent green for pulse
            painter.setBrush(green)
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(center, pulse_radius, pulse_radius)


        # Draw the circle background
        painter.setBrush(QColor(0, 0, 0, 100))  # Semi-transparent black
        painter.drawEllipse(center, radius, radius)

        # Draw the percentage circle
        pen = QPen(color, 10)
        painter.setPen(pen)

        # Draw the percentage arc
        painter.drawArc(center.x() - radius, center.y() - radius, radius * 2, radius * 2, 90 * 16,
                        -int(360 * 16 * (self.volume_percentage / 100)))

        # If muted, draw the small red circle
        if self.muted:
            self.paintMutedCircle(painter, center)

        # Finish painting
        painter.end()

    def paintMutedCircle(self, painter, center):
        """Helper function to draw a small, subtle red circle at the center when muted."""
        small_radius = 15  # Small circle radius
        painter.setBrush(QColor(150, 0, 0, 90))  # Darker red, more transparent
        painter.setPen(Qt.NoPen)  # Optional: remove border for a cleaner look
        painter.drawEllipse(center, small_radius, small_radius)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            print("\n=== Mouse Press Event ===")

            # Process the click
            self.is_dragging = True
            self.drag_position = event.globalPos() - self.pos()
            self.toggle_mute()

            # Restore focus if we have a tracked window
            if self.last_focus_window:
                print(f"Restoring focus to: {self.last_focus_window}")
                self.user32.SetForegroundWindow(self.last_focus_window)
                # Flash the window to ensure focus
                self.user32.FlashWindow(self.last_focus_window, True)

            event.accept()

        elif event.button() == Qt.RightButton:
            current_window = GetForegroundWindow()
            self.open_settings_dialog()
            if current_window:
                self.user32.SetForegroundWindow(current_window)
            event.accept()

    def __del__(self):
        """Clean up when closing"""
        if hasattr(self, 'hook'):
            self.user32.UnhookWinEvent(self.hook)
            self.ole32.CoUninitialize()

    def force_restore_focus(self):
        """More aggressive focus restoration with debug prints"""
        print("\n=== Attempting Focus Restoration ===")
        if self.last_focus_window:
            print(f"1. Trying to restore to window: {self.last_focus_window}")

            # Get current foreground window for comparison
            current_focus = GetForegroundWindow()
            print(f"2. Current focused window before restore: {current_focus}")

            # Try multiple restoration methods
            for attempt in range(1, 4):
                print(f"\nAttempt {attempt}:")

                # Method 1: Simple SetForegroundWindow
                result = SetForegroundWindow(self.last_focus_window)
                print(f" - SetForegroundWindow result: {result}")

                # Method 2: With BlockInput
                windll.user32.BlockInput(True)
                windll.user32.BlockInput(False)
                print(" - BlockInput toggled")

                # Method 3: With Alt key simulation
                windll.user32.keybd_event(0x12, 0, 0, 0)  # Alt down
                windll.user32.keybd_event(0x12, 0, 2, 0)  # Alt up
                print(" - Simulated Alt key press")

                # Verify if it worked
                new_focus = GetForegroundWindow()
                print(f" - New focused window: {new_focus}")
                print(f" - Success: {new_focus == self.last_focus_window}")

                if new_focus == self.last_focus_window:
                    break

                # Small delay between attempts
                # windll.kernel32.Sleep(10)
        else:
            print("No saved window to restore focus to!")

    def toggle_mute(self):
        devices = AudioUtilities.GetMicrophone()
        if not devices:
            return

        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        volume = interface.QueryInterface(IAudioEndpointVolume)

        if self.volume_percentage == 0:
            saved_volume = self.load_volume() / 100.0
            volume.SetMasterVolumeLevelScalar(saved_volume, None)
            self.volume_percentage = self.load_volume()
            self.muted = False
        else:
            volume.SetMasterVolumeLevelScalar(0, None)
            self.volume_percentage = 0
            self.muted = True

        self.update()


    def open_settings_dialog(self):
        # Stop the audio stream when opening settings
        if self.stream:
            self.stream.stop()
            self.stream.close()

        dialog = SettingsDialog(self)
        dialog.exec_()

        # Restart the audio stream after settings are closed
        self.start_audio_stream()

    def mouseMoveEvent(self, event):
        if self.is_dragging:
            # Move the overlay based on the mouse position
            new_position = event.globalPos() - self.drag_position
            self.move(new_position)
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            # Stop dragging
            self.is_dragging = False
            self.save_position()  # Save position when dragging stops
            event.accept()

    # def mouseDoubleClickEvent(self, event):
    #     if event.button() == Qt.LeftButton:
    #         # Open the settings dialog
    #         dialog = SettingsDialog(self)
    #         dialog.exec_()

    def set_volume(self, volume):
        devices = AudioUtilities.GetMicrophone()
        if not devices:
            return

        interface = devices.Activate(
            IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        volume_control = interface.QueryInterface(IAudioEndpointVolume)

        # Set the volume based on the slider value
        volume_control.SetMasterVolumeLevelScalar(volume / 100, None)
        self.volume_percentage = volume
        self.save_volume(volume)  # Save the volume to file
        self.update()

    def set_size(self, size):
        self.setGeometry(self.x(), self.y(), size, size)
        self.save_size(size)  # Save the size to file
        self.update()

    def save_volume(self, volume):
        # Save the volume to a file for persistence
        with open(VOLUME_FILE, "w") as f:
            f.write(str(volume))

    def load_volume(self):
        # Load the volume from a file
        if os.path.exists(VOLUME_FILE):
            with open(VOLUME_FILE, "r") as f:
                return int(f.read())
        return 100  # Default to 100% if no saved volume

    def save_size(self, size):
        # Save the size to a file for persistence
        with open(SIZE_FILE, "w") as f:
            f.write(str(size))

    def load_size(self):
        # Load the size from a file
        if os.path.exists(SIZE_FILE):
            with open(SIZE_FILE, "r") as f:
                return int(f.read())
        return 200  # Default to 200px if no saved size

    def save_position(self):
        # Save the position to a file for persistence
        with open(POSITION_FILE, "w") as f:
            position = self.pos()
            f.write(f"{position.x()},{position.y()}")

    def load_position(self):
        # Load the position from a file
        if os.path.exists(POSITION_FILE):

            with open(POSITION_FILE, "r") as f:
                position_data = f.read().split(",")
                x, y = int(position_data[0]), int(position_data[1])
                return QPoint(x, y)
        return QPoint(10, 10)  # Default to (10, 10) if no saved position

if __name__ == "__main__":
    app = QApplication(sys.argv)
    overlay = MuteOverlay()
    sys.exit(app.exec_())

