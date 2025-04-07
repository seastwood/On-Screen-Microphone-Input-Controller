# On-Screen-Microphone-Input-Controller
This is an on-screen microphone controller overlay button for windows 11. When clicked it sets the volume to 0 or to the user's set "On Volume".

![icon](https://github.com/user-attachments/assets/1cf71ce7-0ea4-4aaf-a393-2a4c47d5f9df)

My use case:
I wanted a simple on screen microphone controller when streaming games to my phone through moonlight. This simply allows me to tap the circle with my finger and turn the mic on or off and providing visible feedback of the volume state of my input microphone. 

- Download the repo and run the exe file in the /dist folder if you wish to use this program.
- The button can be dragged and placed anywhere on the screen.
- Right click the button to open the settings menu to change max volume and set the button size. This is also the only way to close the program.

![image](https://github.com/user-attachments/assets/b7b81d3b-8c06-4b95-86ec-22ca8fa03ffc)

- Games must be played in Borderless/Windowed mode in order for the microphone overlay to be visible.
- If using discord, leave open mic on, or leave open mic on in your game, and control it with this button.
- If you want a button on each side of the screen so either thumb can activate it, just run the exe twice and move the button over.

Example of useage on an iphone with gamepad running moonlight:
![IMG_20250405_122320](https://github.com/user-attachments/assets/ea938592-1cf2-47a9-bfbe-6b524a50c914)
![IMG_20250405_122339](https://github.com/user-attachments/assets/d22c902f-a762-41ae-bafb-9e3797310fe2)


I use VBAN-Talkie on my iPhone to transmit my microphone to my pc. VBAN-Receptor is on my windows 11 PC to receive the sound, and VBAN-Cable is also on my PC to allow the microphone to be used as input. 
- Note: In order for this to work, you must go to the VB Cable Control Panel > Options > and turn on Enable Windows Volume Control.
- 2nd note: I also couldn't get the x64 setup exe for VBAN Cable to function with the control panel. The non-x64 exe worked for me with the control panel but it only installs the drivers and  doesn't appear as an installed application... It was a finnicky uninstall/reinstall until it magically worked on Windows 11. (Hopefully they fix this...)

![image](https://github.com/user-attachments/assets/67aa5c68-4b3a-46bb-bb22-1831efcbfc32)

Future potential improvements:
- visual feedback on the circle of mic input activity (done)
- Add option for multiple on screen buttons that can be modified to hotkeys.
- Hotkey mode
- Ability to edit coloring/opacity of buttons when multiple buttons are implemented.
