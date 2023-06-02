# Question Answering

## Topics

  - [Overview of Question Answering](#overview-of-question-answering)

---

## Overview of Question Answering

One of the best ways to get the model to respond specific answers is to improve the format of the prompt. As covered before, a prompt could combine instructions, context, input, and output indicator to get improved results. While these components are not required, it becomes a good practice as the more specific you are with instruction, the better results you will get. Below is an example of how this would look following a more structured prompt. Given the often factual nature that Question-Answering requires, we should make a quick review of some of our [hyperparameters pointers](./98_Hyperparameters_Overview.md) that can be used to control the output.

> **Note:** In short, the lower the `temperature` the more deterministic the results in the sense that the highest probable next token is always picked. Increasing temperature could lead to more randomness encouraging more diverse or creative outputs. We are essentially increasing the weights of the other possible tokens. In terms of application, we might want to use lower temperature for something like fact-based QA to encourage more factual and concise responses. For poem generation or other creative tasks it might be beneficial to increase temperature.

Give the above, it may make sense to investigate the `temperature` hyperparameter to see how it affects the output.

> **Note:** The `temperature` has been to `=0.25` per the recommendation above and the `max_tokens' has been set to ='1200' to allow for a greater prompt length. 

*Prompt:*
```
You must summarize the results of the ----SEARCH RESULTS---- section in a way that best answers the query listed in the ----USER QUERY--- section with your response going in the ---Response--- section.
 
----USER QUERY----
what ports and connectors does my surface have?

----SEARCH RESULTS----
Ports and connectors Surface Book has the ports you expect from a full -feature laptop. Two full-size USB 3.0 ports Connect a USB accessory like a mouse, printer, Ethernet adapter, USB drive, or smartphone. SD card slot Use the full -size SD card slot with an SD card (sold separately) for extra storage and transferring files. Mini DisplayPort version 1.2a Share what’s on your Surface screen by connecting it to an HDTV, monitor, or projector. (Video adapters are sold separ ately.) 3.5 mm headset jack Plug in your favorite headset for a little more privacy when listening to music or conference calls. Software Windows 10 operating system Windows 10 provides a variety of options for entertainment and productivity whether you ’re at school, at home, or on the go.
Connect devices and accessories You can make photos, videos, and presentations bigger by connecting your Surface Book to a TV, monitor, or projector. Or, connect to an HDTV and watch movies on a big screen. You can connect monitors, accessories, and other devices directly to your Surface Book using the USB ports, Mini DisplayPorts, or Bluetooth. Or, connect everything to a Surface Dock (sold separately). Surface Dock lets you transform your Surface Book into a full desktop PC using a single cable. Set up your workspace with S urface Dock Surface Dock supports high -speed transfer of video, audio, and data. Its compact design gives you flexibility and keeps your desktop clutter -free. The external power supply recharges your Surface and provides plenty of additional power to char ge connected USB devices. Here's how to set up your Surface Dock: 1. Plug the AC end of the Surface Dock power cord into an electrical outlet or power strip and plug the other end into the power port on your Surface Dock. 2. If you want to use a wired network connection, connect a network cable to the Ethernet port on your Surface Dock. 3. Connect your computer peripherals to the USB ports on your Surface Dock. 4. Connect a cable from your monitor to a Mini DisplayPort on your Surfa ce Dock. If your monitor cable doesn’t have a Mini DisplayPort connector, you’ll need to buy another cable or an adapter. For more info on adapters, see Connect Surface to a TV, monitor, or projector on Surface.com. 5. Connect any audio accessories like speakers or headphones.
Microsoft Page 26 DisplayPort or HDMI port, use a VGA cable and the Mini DisplayPort to VGA Adapter. A VGA adapter or cable is for video only. Audio will play from your Surface speakers unless you’ve connected exter nal speakers. For more info, see Surface sound, volume, and audio accessories on Surface.com.  Wireless : You can connect to wireless displays when Windo ws detects one nearby. Or, use a Microsoft Wireless Display Adapter (sold separately) to connect to a screen using Miracast. Connect to a wired display 1. Connect an HDMI or VGA cable to the HDMI, DisplayPort, or VGA port on your TV, monitor, or projector. 2. Connect the other end of the cable to a Surface video adapter or the Mini DisplayPort on your Surface or to your docking station. Mini DisplayPort on Surface Book Mini DisplayPort on Surface Dock 3. If you’re using an adapter, plug it into the Mini DisplayPort on your Surface or your docking station. Connect to a wireless display 1. On your Surface, swipe in from the right edge of the screen or select Action center in the taskbar. 2. Select Connec and in the list of displays, select the name of the wireless display. If you have problems connecting your Surface or have questions about screen resolution, see Trouble connecting Surface to a second screen? on Surface.com. If you’re using a Microsoft Wireless Display Adapter to connect to a screen using Miracast, see Using the Microsoft Wireless Display Adapter with Surface on Surface.com for more info. Set up your screens Once you connect to another screen or screens, you can choose what to display on each screen.

---Response---
```

The source for the ---Search Results--- text above comes from this [Surface User Guide](https://download.microsoft.com/download/7/B/1/7B10C82E-F520-4080-8516-5CF0D803EEE0/surface-book-user-guide-EN.pdf) and is the text from 3 pages within that document.

*Output:*
```
The Surface Book has two full-size USB 3.0 ports, an SD card slot, a Mini DisplayPort version 1.2a, a 3.5 mm headset jack, and the ability to connect to a wired display with an HDMI or VGA cable and a wireless display with Miracast. It also has a Surface Dock (sold separately) for connecting monitors, accessories, and other devices.
```

The response listed above is a concise summarization of the supplied text and it adheres to the source material, namely the text in the ---Search Results--- section. 

---

[Previous Section (Information Extraction)](./02_Information_Extraction.md)

[Next Section (Text Classification)](./04_Text_Classification.md)