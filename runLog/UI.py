from prompt_toolkit.application import Application
from prompt_toolkit.application.current import get_app
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.key_binding.bindings.focus import focus_next, focus_previous
from prompt_toolkit.layout import HSplit, Layout, VSplit, Dimension
from prompt_toolkit.styles import Style
from prompt_toolkit.widgets import Box, Button, Frame, Label, TextArea

RESULT = None
KEYS = None
POS = {}
NEG = {}
CURRID = 0

# Event handlers for all the buttons.
def good_clicked():
    global RESULT, POS, CURRID, KEYS
    if CURRID < 0:
        # initialize button text after introduction is shown in text_area
        GoodRunButton.text = 'Good-run'
        BadRunButton.text = 'Bad-run'
        GoBackButton.text = 'Go Back'
    if CURRID >= 0:
        POS[KEYS[CURRID]] = RESULT[KEYS[CURRID]]
    CURRID = CURRID + 1
    ExitButton.text = 'Exit %d/%d' % (CURRID+1, len(KEYS))
    if CURRID < len(KEYS):
        text_area.text = RESULT[KEYS[CURRID]]
    else:
        get_app().exit()

def bad_clicked():
    global RESULT, NEG, CURRID, KEYS
    if CURRID < 0:
        return
    NEG[KEYS[CURRID]] = RESULT[KEYS[CURRID]]
    CURRID = CURRID + 1
    ExitButton.text = 'Exit %d/%d' % (CURRID+1, len(KEYS))
    if CURRID < len(KEYS):
        text_area.text = RESULT[KEYS[CURRID]]
    else:
        get_app().exit()


def back_clicked():
    global RESULT, CURRID
    if ExitButton.text == 'Confirm Exit':
        # abort exit. Go back to previous run
        GoodRunButton.text = 'Good-run'
        BadRunButton.text = 'Bad-run'
        GoBackButton.text = 'Go Back'
        ExitButton.text = 'Exit %d/%d' % (CURRID+1, len(KEYS))
        text_area.text = RESULT[KEYS[CURRID]]
        return
    if CURRID < 0:
        return
    if CURRID > 0:
        CURRID = CURRID - 1
        # remove previous
        if KEYS[CURRID] in POS:
            del POS[KEYS[CURRID]]
        if KEYS[CURRID] in NEG:
            del NEG[KEYS[CURRID]]
        ExitButton.text = 'Exit %d/%d' % (CURRID+1, len(KEYS))
        text_area.text = RESULT[KEYS[CURRID]]


def exit_clicked():
    global RESULT, POS, NEG, CURRID, KEYS
    if CURRID < 0:
        return
    if ExitButton.text[:4] == 'Exit': # exit button is only pressed once
        ExitButton.text = 'Confirm Exit'
        GoodRunButton.text = ''
        BadRunButton.text = ''
        text_area.text = 'If exit, all runs beyond %s will be considered good runs.' % KEYS[CURRID]
    elif ExitButton.text == 'Confirm Exit':
        for key in KEYS[CURRID:]:
            POS[key] = RESULT[key]
            if key in NEG:
                del NEG[key]
        get_app().exit()


# All the widgets for the UI.
GoodRunButton = Button("Next", handler=good_clicked, width=30)
BadRunButton  = Button("", handler=bad_clicked, width=30)
GoBackButton  = Button("", handler=back_clicked, width=30)
ExitButton    = Button("", handler=exit_clicked,  width=30)
text_area = TextArea(focusable=False)

# Combine all the widgets in a UI.
# The `Box` object ensures that padding will be inserted around the containing
# widget. It adapts automatically, unless an explicit `padding` amount is given.
root_container = Box(
    HSplit(
        [
            Label(text="Is this runLog entry problematic?"),
            VSplit(
                [
                    Box(
                        body=HSplit([GoodRunButton, BadRunButton, GoBackButton, ExitButton], padding=1),
                        padding=1,
                        style="class:left-pane",
                        height=Dimension(preferred=50)
                    ),
                    Box(body=Frame(text_area), padding=1, style="class:right-pane"),
                ]
            ),
        ], width=Dimension(preferred=100)
    ),
)

layout = Layout(container=root_container, focused_element=GoodRunButton)


# Key bindings.
kb = KeyBindings()
kb.add("down")(focus_next)
kb.add("up")(focus_previous)


# Styling.
style = Style(
    [
        ("left-pane", "bg:#888800 #000000"),
        ("right-pane", "bg:#00aa00 #000000"),
        ("button", "#000000"),
        ("button-arrow", "#000000"),
        ("button focused", "bg:#ff0000"),
        ("text-area focused", "bg:#ff0000"),
    ]
)


# Build a main application object.
application = Application(layout=layout, key_bindings=kb, style=style, full_screen=True)


def main(result, intro=''):
    global RESULT, POS, NEG, CURRID, KEYS
    # remove empty entry
    KEYS = []
    RESULT = {}
    for key, content in result.items():
        if content:
            KEYS.append(key)
            RESULT[key] = content
    CURRID = -1
    text_area.text = intro
    application.run()
    return POS, NEG


if __name__ == "__main__":
    results = {1: 'Problematic1 '*100, 2: 'Problematic2', 3: 'Non-problematic3'}
    pos, neg = main(results)
    print(pos, neg)
