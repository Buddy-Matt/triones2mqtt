## requirements

pygatt - pip install pygatt[GATTTOOL]
paho-mqtt - pip install paho-mqtt
pexpect - pip install pexpect

compatible bluez:

yay -Syu bluez-utils-compat

## install

create config.yaml

update triones2mqtt.service to reflect install path

`# systemctl link /path/to/triones2mqtt.service`
`# systemctl enable --now triones2mqtt.service`