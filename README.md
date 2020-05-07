Anki plugin to bury related cards even if they're not siblings.

# Testing

Anki's a bit tough to test around. Instead of trying to hack an Anki testing
environment, this plugin relies heavily on type statements and manual testing.
The manual testing checklist is:

- [ ] read current settings
- [ ] add a new rule
- [ ] delete a rule
- [ ] close Anki to make sure rules persist
- [ ] open Anki and make sure rules load
- [ ] confirm cousins are suppressed
  - create a new deck
  - add Basic cards like
    - `("Basic front 1", "1")`
    - `("Basic front 2", "2")`
    - `("3", "3")`
  -  add a rule to suppress Basic cards when rehearsing a Basic card when the Front side is the same
  - review deck and confirm that the rehearsing suppresses card
