## 🚀 Sensy-One Zone Editor

An official add-on for configuring **polygon detection zones** on **Sensy-One** devices.

![Sensy-One Banner](https://github.com/sensy-one/home-assistant-addons/blob/main/zone-editor/HA.png)

The **Sensy-One Zone Editor** provides a visual interface for creating and adjusting detection zones for Sensy-One sensors. It supports **2D and 3D zone editing**, **live 3D target visualization**, and a **3D KDE/heatmap view** for spatial detection analysis. Up to **three detection zones** and **one exclusion zone** can be configured, with changes applied directly to the device.

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

Create a file named [docker-compose.yaml](https://github.com/sensy-one/home-assistant-addons/blob/main/docker-compose.yaml):

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

Create a [.env](https://github.com/sensy-one/home-assistant-addons/blob/main/.env): file in the same directory:

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

## 🧭 How to Use

* Open the **Zone Editor** from your Home Assistant sidebar
* Select your **device** from the dropdown menu
* Choose which zone you want to configure (**Zone 1**, **Zone 2**, **Zone 3**, or **Exclusion**)
* Click directly on the **radar canvas** to place up to **8 points** and shape your zone
* Click **Save** — your configuration is instantly applied to your device


## 💬 Let's Connect

Your feedback helps us improve. Whether you’ve found a bug, need help, or want to suggest a feature — we’re listening.

**Discord:**
Join our community and get support on the [Discord server](https://discord.gg/TB78Wprn66).

**GitHub Issues:**
Found a bug or have a suggestion? Report it on the [GitHub Issues page](https://github.com/sensy-one/home-assistant-addons/issues).