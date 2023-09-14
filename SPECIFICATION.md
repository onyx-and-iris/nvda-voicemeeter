# Software Specification

## Description

A remote control utility for Voicemeeter designed to be used with the NVDA screen reader.

## Requirements

#### Functional Goals

- Parameter updates caused by user input should be read back to the user via the screen reader.
- When focusing a control the current value for that control should be read back to the user.
- The application should scale correctly according to each kind of Voicemeeter (basic, banana, potato). This means the following:
  - Correct number of strips/buses.
  - Correct number of bus assignments for each strip.
  - Where certain controls are valid for one kind they may not be for another.
- Where possible set limits on data entry and keep controls appropriate for the type of parameter.

#### Accessibility Goals

- Every control must be usable with a keyboard.
- Navigation around the application must be doable with a keyboard.
- Should use standard Windows controls only.

## Limitations

- May not cover 100% of the Voicemeeter GUI, for example the many EQ parameters.
- Only designed to work with the NVDA screen reader. Other screen readers not supported.
- Only the main Voicemeeter GUI supported by this application. No support for Matrix or other Voicemeeter products.
- Runs on Python version 3.10 or greater.
