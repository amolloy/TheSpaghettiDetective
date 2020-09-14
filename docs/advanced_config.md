
# Advanced server configuration

## Using a reverse proxy

You can set up a reverse proxy in front of The Spaghetti Detective server.

Two configuration items need to be set differently if you are using a reverse proxy.

### 1. "Domain name" in Django site configuration.

1. Open Django admin page at `http://tsd_server_ip:3334/admin/`.

2. Login with username `root@example.com`.

3. On Django admin page, click "Sites", and click the only entry "example.com" to bring up the site you need to configure. Set "Domain name" as follows:

Suppose:

* `reverse_proxy_ip`: The public IP address of your reverse proxy. If you use a domain name for the reverse proxy, this should the domain name.
* `reverse_proxy_port`: The port of your reverse proxy.

The "Domain name" needs to be set to `reverse_proxy_ip:reverse_proxy_port`. The `:reverse_proxy_port` part can be omitted if it is standard 80 or 443 port.

### 2. If the reverse proxy is accessed through HTTPS:

1. Open `docker-compose.yml`, find `SITE_USES_HTTPS: 'False'` and replace it with `SITE_USES_HTTPS: 'True'`.

2. Restart the server: `docker-compose restart`.

### NGINX

Please note that this is not a general guide. Your situation/configuration may be different.

* This configuration does a redirect from port 80 to 443.
* This config is IP agnostic meaning it should work for IPv4 or IPv6.
* This config supports HTTP/2 as well as HSTS TLSv1.3/TLSv1.2, please do note that anything relying on a websocket runs over http1.1.

```
server {
  listen 80;
  listen [::]:80;
  server_name YOUR.PUBLIC.DOMAIN.HERE.com;
  return 301 https://$host$request_uri;
}
server {
  listen 443 ssl http2;
  listen [::]:443 ssl http2;
  ssl_certificate /YOUR/PATH/HERE/fullchain.pem;
  ssl_certificate_key /YOUR/PATH/HERE/privkey.pem;
  ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-SHA384;
  ssl_prefer_server_ciphers on;
  ssl_stapling on;
  ssl_stapling_verify on;
  ssl_protocols TLSv1.3 TLSv1.2;
  ssl_early_data on;
  proxy_set_header Early-Data $ssl_early_data;
  ssl_dhparam /etc/ssl/certs/dhparam.pem;
  ssl_ecdh_curve secp384r1;
  ssl_session_cache shared:SSL:40m;
  ssl_session_timeout 4h;
  add_header Strict-Transport-Security "max-age=63072000;";
  server_name YOUR.PUBLIC.DOMAIN.HERE.com;
  access_log /var/log/tsd.access.log;
  error_log /var/log/tsd.error.log;
  location / {
    proxy_pass http://YOUR BACKEND IP/HOSTNAME:3334/;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header Host $http_host;
    proxy_set_header X-Forwarded-Proto https;
    proxy_redirect off;
    client_max_body_size 10m;
  }
 location /ws/ {
    proxy_pass http://YOUR BACKEND IP/HOSTNAME:3334/ws/;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "Upgrade";
  }
}
```

### Traefik

1. [Follow these instructions on how to setup Traefik (First two steps)](https://www.digitalocean.com/community/tutorials/how-to-use-traefik-as-a-reverse-proxy-for-docker-containers-on-debian-9)

1. Navigate to your directory of TheSpaghettiDetective `cd TheSpaghettiDetective`

1. Edit the docker-compose.yml file with your favorite editor: `nano docker-compose.yml`

1. Add `labels:` and `networks:` to the `web:` section, and also add `networks:` at the end of the file:

    ```
    ...
      web:
        <<: *web-defaults
        hostname: web
        ports:
          - 3334:3334
        labels:
          - traefik.backend=thespaghettidetective
          - traefik.frontend.rule=Host:spaghetti.your.domain
          - traefik.docker.network=web
          - traefik.port=3334
        networks:
          - web
        depends_on:
          - ml_api
        command: sh -c "python manage.py collectstatic --noinput && python manage.py migrate && python manage.py runserver 0.0.0.0:3334"

      ...

      ...

        networks:
          web:
            external: true
      ```

1. Start TheSpaghettiDetective with `docker-compose up -d`

1. You should now be able to browse to `spaghetti.your.domain`

## Running TSD with Nvidia GPU acceleration

This is only available on Linux based host machines

In addition to the steps in [README](../README.md), you will need to:

- [Install Cuda driver](https://docs.nvidia.com/cuda/cuda-installation-guide-linux/index.html) on your server.
- [Install nvidia-docker](https://github.com/NVIDIA/nvidia-docker).
- Run this command in `TheSpaghettiDetective` directory:
```
cat >docker-compose.override.yml <<EOF
version: '2.4'

services:
  ml_api:
    runtime: nvidia
EOF
```
- Restart the docker cluster by running `docker-compose down && docker-compose up -d`

## Running on Nvidia Jetson hardware

[Document Here](jetson_guide.md)

## Running on unRAID

[Document Here](unraid_guide.md)

## Enable telegram notifications

1. Create a bot. You can do this by messaging [@BotFather](https://t.me/botfather) - see [telegram's documentation](https://core.telegram.org/bots#3-how-do-i-create-a-bot) for further information.
2. Add TELEGRAM_BOT_TOKEN to docker-compose.yml with the token @BotFather generated.
3. Set the bot's domain by messaging @BotFather `/setdomain`, selecting your bot, and sending him your bot's domain name. This must be a publicly-accessible domain name. You can temporarily generate a publicly-accessible domain name through a local tunnel - see [https://localtunnel.github.io/www/] or [https://serveo.net/#manual] for two good options.
4. Log in to telegram from your user preferences page (let's say your publicly accessible domain name is `https://tunnel.serveo.net/`. You'd go to `https://tunnel.serveo.net`, log into your local TheSpaghettiDetective account -- by default `root@example.com` -- and go to the user preferences page, then log into telegram and hit the form's `save` button).
5. That's it! Once you've logged in once, you will no longer need a publicly-accessible domain name.

## Enable social login (TBD)

## Change email server to be one other than `sendmail` on localhost (TBD)
