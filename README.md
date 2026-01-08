# VolumeMixer

A StreamController plugin for managing audio volumes through PulseAudio.

## Actions

- **OpenVolumeMixer**: Opens the volume mixer interface page and allows configuring the volume increment percentage.
- **ExitVolumeMixer**: Exits the volume mixer interface and returns to the previous page.
- **MoveLeft**: Navigates left to view additional audio inputs when more inputs exist than can be displayed at once.
- **MoveRight**: Navigates right to return to previously viewed audio inputs in the volume mixer.
- **VolumeUpKey**: Increases the volume of the associated audio input by the configured increment amount.
- **VolumeDownKey**: Decreases the volume of the associated audio input by the configured increment amount.
- **MuteKey**: Toggles the mute state of the associated audio input.
- **Dial**: Controls audio input volume via dial rotation and toggles mute with a short press (for Stream Deck Plus).