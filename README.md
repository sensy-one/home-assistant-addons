## 🚀 Sensy-One Zone Editor

An official add-on for configuring polygon-based detection zones on Sensy-One devices using a 2D and 3D floorplan, with live sensor visualization and 3D heatmap analysis.

![Sensy-One Banner](https://github.com/sensy-one/home-assistant-addons/blob/main/zone-editor/HA.png)

The Sensy-One Zone Editor provides a visual interface for designing and managing detection zones for Sensy-One sensors. It supports 2D and 3D floorplan editing, live sensor visualization, and 3D target and heatmap views.

## ⚙️ Installation (Home Assistant Add-on)

* Open **Home Assistant**
* Go to **Settings → Add-ons → Add-on Store**
* Open the **menu (three dots)** and select **Repositories**
* Add the custom repository URL: [https://github.com/sensy-one/home-assistant-addons](https://github.com/sensy-one/home-assistant-addons)
* Search for **Sensy-One Zone Editor**
* Click **Install**, then **Start**
* *(Optional)* Enable **Show in sidebar** for quick access

## 🐳 Installation (Docker Standalone)

For advanced users or custom setups, the Zone Editor can also be run as a standalone Docker container connected to your existing Home Assistant instance.

### docker-compose setup

Create a file named [docker-compose.yaml](https://github.com/sensy-one/home-assistant-addons/blob/main/zone-editor/docker-compose.yaml)

```yaml
services:
  zone-editor:
    image: ghcr.io/sensy-one/zone-editor:latest
    container_name: sensy-zone-editor
    environment:
      - HA_URL=http://${HOME_ASSISTANT_IP:-homeassistant.local}:8123
      - HA_TOKEN=${LONG_LIVED_ACCESS_TOKEN?error}
    ports:
      - 8099:8099
```

Create in the same directory a file named [.env](https://github.com/sensy-one/home-assistant-addons/blob/main/zone-editor/.env) 

```env
HOME_ASSISTANT_IP=your_home_assistant_ip_here
LONG_LIVED_ACCESS_TOKEN=your_long_lived_access_token_here
```

Start the container:

```bash
docker compose up -d
```

Open in your browser:

```
http://<IP_OF_THE_MACHINE_RUNNING_DOCKER>:8099
```

## 🧭 Editor Overview

* Watch the short walkthrough on [YouTube](https://youtu.be/y40BqbnXp_g)

* In Floorplan mode, the Draw Walls tool in the bottom-right toolbar is used to define the layout by placing wall segments directly on the canvas. Walls can be drawn by clicking to place points, or by entering exact distances in centimeters for precise placement. Right-click ends the current wall and allows a new wall to be started, for example when drawing interior walls.

* Sensors are placed using the Place Sensor tool in the bottom-right toolbar. Select the desired sensor from the dropdown and click on the canvas to place it. Once placed, the sensor can be rotated or repositioned using its field-of-view handles.

* Detection zones are created using the Draw Polygons tool in the bottom-right toolbar. With a sensor selected, polygon-based zones can be drawn directly on the floorplan to define detection areas.

* Controls, Hold Shift and drag with the mouse to pan. Drag with the mouse (without Shift) to orbit.

## 💬 Let's Connect

Your feedback helps us improve. Whether you’ve found a bug, need help, or want to suggest a feature — we’re listening.

**Discord:**
Join our community and get support on the [Discord server](https://discord.gg/TB78Wprn66).

**GitHub Issues:**
Found a bug or have a suggestion? Report it on the [GitHub Issues page](https://github.com/sensy-one/home-assistant-addons/issues).