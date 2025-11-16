# Bravia Remote Control API

This simple API for Sony Bravia Televisions can be run at home to expose a limited set of remote control functionality
to the Internet. This application can be used, for example, to provide an interface to Amazon Alexa for older TVs that
do not natively support it, or as part of a custom home automation setup.

## Requirements

 * An always-on computer capable of running Python 3.10 or Docker (with docker-compose)
 * Knowledge of using Docker _OR_ comfort with the command-line.
 * A configured web server such as nginx that supports reverse proxy
 * Optionally, a knowledge of setting up SSL certificates
 * A Sony Bravia Android TV with the remote control API enabled

## Setup Instructions

### 1. Enable your TV's API
Your television must have a pre-shared key enabled to access its API. [Find the instructions and observe the warning here.](https://braviaproapi.readthedocs.io/en/latest/gettingstarted.html#configuring-your-television)

### 2. Download the application
Download the latest release or current source from this repository and extract it to your server computer. If running from source, you will only need the contents of the `src` directory.

### 3. Edit the API configuration
Rename `sample.env` to `.env`. Set up the following options (**DO NOT use quotes!**):

 * `BRAVIA_API_KEY` - The passphrase used to access your API. Must be at least 32 characters and cannot contain spaces.
 * `BRAVIA_DEVICE_HOST` - The IP address or hostname of your TV.
 * `BRAVIA_DEVICE_PASSCODE` - The pre-shared key you configured on your TV.

### 4. Create an SSL certificate
**NOTE:** If you are confused by this step, you should seek out information elsewhere before continuing, or stop.

* If you're using a domain name to access the server and feel comfortable with it, use a service like [Let's Encrypt](https://letsencrypt.org/) to create an SSL certificate to protect your API.

* If you are going to access the API by IP address or don't care that much about security, run the following and fill out the prompts to create a self-signed certificate. This requires OpenSSL and its CLI tools to be installed.
  ```bash
  openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout nginx-selfsigned.key -out nginx-selfsigned.crt
  ```

Place the certificate and key files somewhere safe where your web server can read them.

### 5. Set up the reverse proxy
Use the supplied `nginx.sample.conf` configuration file or supply your own for your web server of choice. If using the supplied file, be sure to update the values as appropriate for your setup.

### 6. Run the API server

#### Running with Docker (preferred, all platforms)
From a terminal, navigate to your extracted directory and run:

```bash
docker-compose up
```

Note that if you make changes to the application code, you will need to `docker-compose down` and `docker-compose build`
before running again.

#### Running with native Python
**NOTE:** These instructions assume you are using Linux or macOS. If using Windows, consider running in WSL or modifying the steps to work with Windows tooling.

  1. From a terminal, navigate to your extracted directory and install the Python dependencies:
  ```bash
  pip install pipenv
  pipenv install
  ```
  2. Run the server:
  ```bash
  pipenv run gunicorn -b 0.0.0.0:5000 -w 1 --preload wsgi:app
  ```

## API Documentation

### Sending Requests
All requests are POST and use query parameters to pass arguments. An `X-Auth-Key` header containing your configured API key.

Here's a sample CURL request:
```
$ curl -X POST https://127.0.0.1/power/on/ -H 'X-Auth-Key: 12341234123412341234123412341234'

{"status": "ok"}
```

### Responses
All requests respond with JSON containing at least `status` (which is `ok` or `error`). If an error occurs, an `error` property will also be returned. Some API endpoints may return additional properties.

Sample success response:
```JSON
{"status": "ok"}
```

Sample error response:
```json
{"status": "error", "error": "Invalid power status specified, must be 'on' or 'off'"}
```

### General Endpoints

Gets information about the API

* **GET /status/** - Returns the API version currently running.
  * `{"status": "ok", "version": "1.0.0"}` (HTTP 200)

### Power endpoints

Controls the device's sleep/wake state

* **POST /power/on/** - Wakes the device
* **POST /power/off/** - Puts the device to sleep
* **GET /power/** Returns the power status as a boolean
  * `{"status": "ok", "is_awake": true}` (HTTP 200)

### Volume endpoints

Controls the device's audio volume

* **POST /volume/set/\<level\>/** - Sets the volume of the device's speakers. `<level>` is an integer between 0 and 100, inclusive.

* **POST /volume/mute/** - Mutes the device's speakers.

* **POST /volume/unmute/** - Unmutes the device's speakers.

* **GET /volume/** - Returns the current volume status:
  * `{"status": "ok", "volume": {"level": 15, "muted": false}}` (HTTP 200)

### App endpoints

Controls apps on the device

* **POST /apps/launch/\<name\>/** - Launches the app with a name most similar to `<name>` (uses fuzzy search). Returns the app opened.
  * `{"status": "ok", "app_name": "FunimationNow"}` (HTTP 200)
  * `{"status": "error", "error": "Could not locate app"}` (HTTP 404)

* **GET /apps/** - Returns a list of apps on the device as an array
  * `{"status": "ok", "apps": ["FunimationNow", "Crunchyroll", "YouTube"]}` (HTTP 200)

### Input endpoints

Controls external input sources on the device

* **POST /input/set/\<name\>/** - Switches to the input with a name OR custom display label most similar to `<name>` (uses fuzzy search). Returns the input found.
  * `{"status": "ok", "input": {"custom_label": "AppleTV", "name": "HDMI 1/MHL"}}` (HTTP 200)
  * `{"status": "error", "error": "Could not locate input"}` (HTTP 404)

* **GET /input/** - Returns the currently displayed input.
  * `{"status": "ok", "input_name": "Video/Component"}` (HTTP 200)
  * `{"status": "error", "error": "Not currently displaying an external input"}` (HTTP 404)

* **GET /input/all/** - Returns all available inputs.
  * Example response:
  ```
  {
      "status": "ok",
      "inputs": [
          {"name": "AppleTV", "custom_label": null},
          {"name": "HDMI 1/MHL", "custom_label": "Switch"}
      ]
  }
  ```

### Channel endpoints

Controls TV channels on the device. These endpoints only support analog and ATSC digital channels.

* **POST /channel/number/\<number\>/** - Switches to the channel number specified in `<number>`. Returns the channel found. The number may be in format `X`, `X.Y`, or `X-Y`. If no subchannel is specified, a matching analog channel will be preferred over a matching digital channel.
  * `{"status": "ok", "channel": "7.1", "name": "WXYZ-HD", "type": "digital"}` (HTTP 200)
  * `{"status": "error", "error": "The selected channel is not available"}` (HTTP 404)
  * `{"status": "error", "error": ""Channel number must be in numeric format 'X' or 'X.Y' or 'X-Y'""}` (HTTP 400)

* **POST /channel/name/\<name\>/** - Switches to the channel with a name most closely matching `<name>` (uses fuzzy search). Returns the channel found.
  * `{"status": "ok", "channel": "7.1", "name": "WXYZ-HD", "type": "digital"}` (HTTP 200)
  * `{"status": "error", "error": "Could not locate a matching channel"}` (HTTP 404)
  * `{"status": "error", "error": ""Channel number must be in numeric format 'X' or 'X.Y' or 'X-Y'""}` (HTTP 400)

* **GET /channel/** - Returns all available channels. The `type` field can be either `digital` or `analog`. Analog channels do not have a `name`.
  * Example response:
  ```
  {
      "status": "ok",
      "channels": [
          {"channel": "7.1", "name": "WXYZ-HD", "type": "digital"},
          {"channel": "7.2", "name": "WXYZ-BN", "type": "digital"},
          {"channel": "9", "name": None, "type": "analog"}
      ]
  }
  ```

### Navigation endpoints

Controls navigation, like a remote control.

 * **POST /home/** - Goes to the home screen
 * **POST /playback/\<action\>/** - Controls playback; `<action>` can be any of `play`, `pause`, `stop`, `forward`, `reverse`, `previous`, `next`. Note that in some cases you may need to send `previous` twice rapidly to go back to the previous track instead of the beginning of the current track.

## Contributing
Contributions are welcome! If you see a problem or would like a feature, create an issue or open a pull request on this repository.

## License
This application is distributed with the MIT license. See the LICENSE file for more information.
