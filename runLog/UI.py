from prompt_toolkit.application import Application
from prompt_toolkit.application.current import get_app
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.key_binding.bindings.focus import focus_next, focus_previous
from prompt_toolkit.layout import HSplit, Layout, VSplit, Dimension
from prompt_toolkit.styles import Style
from prompt_toolkit.widgets import Box, Button, Frame, Label, TextArea
from prompt_toolkit.key_binding.bindings.page_navigation import scroll_one_line_up, scroll_one_line_down
from enum import Enum

TEXT = Enum('TEXT', 'BRIEF DETAIL', start=0)
STATUS = Enum('STATUS', 'GOOD BAD NOTSELECTED', start=0)

RESULT = None
KEYS = None
IDSTATUS = [] 
CURRID = 0
TEXTTYPE = TEXT.BRIEF
MULTABLE = False # disable left/right arrow if not multable
HIGHLIGHT = None # should be list of True/False with CURRID as index. Color on text area changes if True

def on_change():
    GoBackButton.text = 'Go Back'
    ExitButton.text = 'Exit %d/%d' % (CURRID+1, len(KEYS))
    if CURRID < len(KEYS):
        if IDSTATUS[CURRID] == STATUS.GOOD:
            GoodRunButton.text = 'Good-run*'
        else:
            GoodRunButton.text = 'Good-run'
        if IDSTATUS[CURRID] == STATUS.BAD:
            BadRunButton.text = 'Bad-run*'
        else:
            BadRunButton.text = 'Bad-run'
        text_area.text = RESULT[KEYS[CURRID]][TEXTTYPE.value]
    else:
        get_app().exit()


# Event handlers for all the buttons.
def good_clicked():
    global RESULT, IDSTATUS, CURRID, KEYS, MULTABLE
    if GoodRunButton.text == '':
        return #button disabled if text on button is removed
    if CURRID >= 0:
        IDSTATUS[CURRID] = STATUS.GOOD
    CURRID = CURRID + 1
    MULTABLE = True
    on_change()

def bad_clicked():
    global RESULT, IDSTATUS, CURRID, KEYS, MULTABLE
    if BadRunButton.text == '':
        return 
    if CURRID >= 0:
        IDSTATUS[CURRID] = STATUS.BAD
    CURRID = CURRID + 1
    MULTABLE = True
    on_change()


def back_clicked():
    global RESULT, CURRID, MULTABLE
    if ExitButton.text == 'Confirm Exit':
        # abort exit. Go back to previous run
        MULTABLE = True
        on_change()
        return
    if CURRID < 0:
        return
    if CURRID > 0:
        CURRID = CURRID - 1
        MULTABLE = True
        on_change()


def exit_clicked():
    global RESULT, IDSTATUS, CURRID, KEYS, MULTABLE
    if CURRID < 0:
        return
    if ExitButton.text[:4] == 'Exit': # exit button is only pressed once
        ExitButton.text = 'Confirm Exit'
        GoodRunButton.text = ''
        BadRunButton.text = ''
        text_area.text = 'If exit, all runs beyond %s will be considered good runs.' % KEYS[CURRID]
        MULTABLE = False
    elif ExitButton.text == 'Confirm Exit':
        for i in range(CURRID, len(KEYS)):
            IDSTATUS[i] = STATUS.GOOD
        get_app().exit()


# All the widgets for the UI.
GoodRunButton = Button("Next", handler=good_clicked, width=30)
BadRunButton  = Button("", handler=bad_clicked, width=30)
GoBackButton  = Button("", handler=back_clicked, width=30)
ExitButton    = Button("", handler=exit_clicked,  width=30)
text_area = TextArea(focusable=False, scrollbar=True)
def get_style() -> str:
    if HIGHLIGHT is not None and CURRID >= 0 and CURRID < len(HIGHLIGHT):
        if HIGHLIGHT[CURRID]:
            return 'class:right-pane-bad'
    return 'class:right-pane'
text_area_box = Box(body=Frame(text_area), padding=1, style=get_style, height=Dimension(max=100))


# Combine all the widgets in a UI.
# The `Box` object ensures that padding will be inserted around the containing
# widget. It adapts automatically, unless an explicit `padding` amount is given.
root_container = Box(
    HSplit(
        [
            Label(text="Control with (up, down, left, right), Pg Up, Pg Down and Enter keys. Shortcut: q is good-run, w is bad-run and tab is go back."),
            VSplit(
                [
                    Box(
                        body=HSplit([GoodRunButton, BadRunButton, GoBackButton, ExitButton], padding=1),
                        padding=1,
                        style="class:left-pane",
                        height=Dimension(preferred=50)
                    ),
                    text_area_box
                ]
            ),
        ], width=Dimension(preferred=110)
    ),
)

layout = Layout(container=root_container, focused_element=GoodRunButton)


# Key bindings.
# also bind wasd for laptop users with not arrow keys
kb = KeyBindings()
kb.add("down")(focus_next)
kb.add("up")(focus_previous)

@kb.add("left")
def _(event):
    global TEXTTYPE
    if MULTABLE and TEXTTYPE == TEXT.DETAIL:
        TEXTTYPE = TEXT.BRIEF
        text_area.text = RESULT[KEYS[CURRID]][TEXTTYPE.value]

@kb.add("right")
def _(event):
    global TEXTTYPE
    if MULTABLE and TEXTTYPE == TEXT.BRIEF:
        TEXTTYPE = TEXT.DETAIL
        text_area.text = RESULT[KEYS[CURRID]][TEXTTYPE.value]

@kb.add("pageup")
def _(event):
    w = event.app.layout.current_window
    event.app.layout.focus(text_area.window)
    scroll_one_line_up(event)
    event.app.layout.focus(w)

@kb.add("pagedown")
def _(event):
    w = event.app.layout.current_window
    event.app.layout.focus(text_area.window)
    scroll_one_line_down(event)
    event.app.layout.focus(w)

@kb.add("w")
def _(event):
    event.app.layout.focus(BadRunButton)
    bad_clicked()

@kb.add("q")
def _(event):
    event.app.layout.focus(GoodRunButton)
    good_clicked()

@kb.add('tab')
def _(event):
    event.app.layout.focus(GoBackButton)
    back_clicked()



# Styling.
style = Style(
    [
        ("left-pane", "bg:#888800 #000000"),
        ("right-pane", "bg:#00aa00 #000000"),
        ("right-pane-bad", "bg:#aa0000 #000000"),
        ("button", "#000000"),
        ("button-arrow", "#000000"),
        ("button focused", "bg:#ff0000"),
        ("text-area focused", "bg:#ff0000"),
    ]
)


# Build a main application object.
application = Application(layout=layout, key_bindings=kb, style=style, full_screen=True)


def main(result, badKeys=None, intro=''):
    global RESULT, IDSTATUS, CURRID, KEYS, TEXTTYPE, HIGHLIGHT
    # remove empty entry
    KEYS = []
    RESULT = {}
    GoodRunButton.text = "Next"
    BadRunButton.text = ""
    GoBackButton.text = ""
    ExitButton.text = "" 
    TEXTTYPE = TEXT.BRIEF
    HIGHLIGHT = []

    # hash table is more efficient for lookup
    badKeys = set(badKeys)

    for key, content in result.items():
        KEYS.append(key)
        if badKeys is not None and key in badKeys:
            HIGHLIGHT.append(True)
        else:
            HIGHLIGHT.append(False)
        RESULT[key] = content
        IDSTATUS.append(STATUS.NOTSELECTED)

    CURRID = -1
    text_area.text = intro
    application.run()
    pos = {}
    neg = {}
    for status, key in zip(IDSTATUS, KEYS):
        if status == STATUS.GOOD:
            pos[key] = result[key]
        elif status == STATUS.BAD:
            neg[key] = result[key]
        else:
            raise RuntimeError('Selection incomplete. This should not have happened.')
    return pos, neg


if __name__ == "__main__":
    results = {1: ['brief1', 'Problematic1 '], 2: ['brief2', 'Problematic2'], 3: ['brief3', 'Non-problematic3']}
    pos, neg = main(results, [1, 3])
    print(pos, neg)
