# rpi-home-assistant
Home Assistant Stuff

- curl -sSL https://get.docker.com | sh
- sudo usermod -aG docker pi
- sudo systemctl enable docker
- sudo systemctl start docker

- docker build -t hass .
- docker run --restart=always -d --name hass --net=host -v /etc/localtime:/etc/localtime:ro -v /home/pi/rpi-home-assistant/configuration:/config hass
