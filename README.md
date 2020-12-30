Anki plugin to bury related cards even if they're not siblings. Configure rules
so you can suppress similar cards from different notes. These rules can are
also used in identifying duplicate cards in the card browser.

# Configuring Rules

To configure, go to "Tools" > "Add-Ons" and select the "Bury Cousins" plugin
and click "Config". In that menu you can rules for burying cards like "When
reviewing a cloze deletion, bury any cloze cards whose text field is very
similar to the reviewed card's text field" or "when reviewing a basic card,
bury any basic cards whose Front field starts with the same characters as the
reviewed cards Front field"

File or fix bugs here:
<a href="https://github.com/AlexRiina/anki_cousins" rel="nofollow">https://github.com/AlexRiina/anki_cousins</a>

# Available Rules

**Similarity** scores fields on fuzzy similarity so "xxxyyy" and "xxyxyy" have
a high match score similar but not super high.

This test requires that the shorter field is at least 4 characters.

**Prefix** looks at the percentage of the longer field that matches the shorter
field so "1234567" and "123" match on the first 3 characters so their match
score is 3/7.

This test requires that the shorter card has at least 4 characters.

**Contains** looks at whether the base field contains the second field exactly,
regardless of the threshold you set.

This test requires that the shorter field is at least 4 characters.

**Contained by** looks at whether the exact base field is contained by the second
field, regardless of threshold set. This is the reverse of **contains**.

This test requires that the shorter field is at least 4 characters.

**Cloze contained by** looks at whether cloze answers in the base field are in
the second field. So if you have a cloze deletion like
`Rabbit babies are {{c1::altrical::precocial / altricial}}`
but don't want to see the definition of that word in the same session, you can
suppress the definition card using "cloze contained by."

This test is limited to answers with at least 4 characters and requires a word
break surrounding the answer to protect against some common cases like testing
the spanish article for water with `{{c1::el::el / la}} agua` from suppressing
all cards containing `el`.

# Development

The easiest way to work on this locally is to clone this repo and symlink the
src folder into your anki plugins. This will register a plugin which will share
settings with any other copy of this plugin that you have installed.

On linux, with my Anki installation, this can be done by

```sh
git clone git@github.com:AlexRiina/anki_cousins.git
cd anki_cousins
make develop
```

To avoid overwriting your main settings while working on this plugin, you can
either modify the `SettingsManager.key` or create a test profile in Anki
(File -> Switch Profiles) and develop against that collection.

# Testing

Anki's a bit tough to test around. Instead of trying to hack an Anki testing
environment, this plugin relies heavily on type statements and manual testing.

To run the small automated linters and tests, run `make test`.

The manual testing checklist is:

1. read current settings
1. add a new rule
1. delete a rule
1. close Anki to make sure rules persist
1. open Anki and make sure rules load
1. confirm cousins are suppressed
    1. create a new deck
    1. add Basic cards like
        - `("Basic front 1", "1")`
        - `("Basic front 2", "2")`
        - `("3", "3")`
  1.  add a rule to suppress Basic cards when rehearsing a Basic card when the Front side is the same
  1. review deck and confirm that the rehearsing suppresses card
