from wx.lib.intctrl import *
import types, string
from sys import maxsize
MAXINT = maxint     # (constants should be in upper case)
MININT = -maxint-1
#----------------------------------------------------------------------------

class HexValidator(IntValidator):
    def __init__(self):
        IntValidator.__init__(self)
        EVT_CHAR(self, self.OnChar)

    def OnChar(self, event):
        """
        Validates keystrokes to make sure the resulting value is a legal
        hex value.  Erasing the value causes it to be set to 0, with the value
        selected, so it can be replaced.  Similarly, replacing the value
        with a '-' sign causes the value to become -1, with the value
        selected."
        """
        key = event.KeyCode()
        ctrl = event.GetEventObject()

        value = ctrl.GetValue()
        textval = TextCtrl.GetValue(ctrl)
        allow_none = ctrl.IsNoneAllowed()

        pos = ctrl.GetInsertionPoint()
        sel_start, sel_to = ctrl.GetSelection()
        select_len = sel_to - sel_start

# (Uncomment for debugging:)
##        print 'keycode:', key
##        print 'pos:', pos
##        print 'sel_start, sel_to:', sel_start, sel_to
##        print 'select_len:', select_len
##        print 'textval:', textval

        # set defaults for processing:
        allow_event = 1
        set_to_none = 0
        set_to_zero = 0
        set_to_minus_one = 0
        paste = 0
        internally_set = 0

        new_value = value
        new_text = textval
        new_pos = pos

        # Validate action, and predict resulting value, so we can
        # range check the result and validate that too.

        if key in (WXK_DELETE, WXK_BACK, WXK_CTRL_X):
            if select_len:
                new_text = textval[:sel_start] + textval[sel_to:]
            elif key == WXK_DELETE and pos < len(textval):
                new_text = textval[:pos] + textval[pos+1:]
            elif key == WXK_BACK and pos > 0:
                new_text = textval[:pos-1] + textval[pos:]
            # (else value shouldn't change)

            if new_text in ('', '-'):
                # Deletion of last significant digit:
                if allow_none and new_text == '':
                    new_value = None
                    set_to_none = 1
                else:
                    new_value = 0
                    set_to_zero = 1
            else:
                try:
                    new_value = ctrl._fromGUI(new_text)
                except ValueError:
                    allow_event = 0


        elif key == WXK_CTRL_V:   # (see comments at top of file)
            # Only allow paste if number:
            paste_text = ctrl._getClipboardContents()
            new_text = textval[:sel_start] + paste_text + textval[sel_to:]
            if new_text == '' and allow_none:
                new_value = None
                set_to_none = 1
            else:
                try:
                    # Convert the resulting strings, verifying they
                    # are legal integers and will fit in proper
                    # size if ctrl limited to int. (if not,
                    # disallow event.)
                    new_value = ctrl._fromGUI(new_text)
                    if paste_text:
                        paste_value = ctrl._fromGUI(paste_text)
                    else:
                        paste_value = 0
                    new_pos = sel_start + len(str(paste_value))

                    # if resulting value is 0, truncate and highlight value:
                    if new_value == 0 and len(new_text) > 1:
                        set_to_zero = 1

                    paste = 1

                except ValueError:
                    allow_event = 0


        elif key < WXK_SPACE or key > 255:
            pass    # event ok


        elif chr(key) == '-':
            # Allow '-' to result in -1 if replacing entire contents:
            if( value is None
                or (value == 0 and pos == 0)
                or (select_len >= len(str(abs(value)))) ):
                new_value = -1
                set_to_minus_one = 1

            # else allow negative sign only at start, and only if
            # number isn't already zero or negative:
            elif pos != 0 or (value is not None and value < 0):
                allow_event = 0
            else:
                new_text = '-' + textval
                new_pos = 1
                try:
                    new_value = ctrl._fromGUI(new_text)
                except ValueError:
                    allow_event = 0


        elif chr(key) in string.digits + "abcdef":
            # disallow inserting digits before the minus sign:
            if value is not None and value < 0 and pos == 0:
                allow_event = 0
            else:
                new_text = textval[:sel_start] + chr(key) + textval[sel_to:]
                try:
                    new_value = ctrl._fromGUI(new_text)
                except ValueError:
                    allow_event = 0

        else:
            # not a legal char
            allow_event = 0


        if allow_event:
            # Do range checking for new candidate value:
            if ctrl.IsLimited() and not ctrl.IsInBounds(new_value):
                allow_event = 0
            elif new_value is not None:
                # ensure resulting text doesn't result in a leading 0:
                if not set_to_zero and not set_to_minus_one:
                    if paste:
                        # Always do paste numerically, to remove
                        # leading/trailing spaces
                        CallAfter(ctrl.SetValue, new_value)
                        CallAfter(ctrl.SetInsertionPoint, new_pos)
                        internally_set = 1

                if allow_event:
                    ctrl._colorValue(new_value)   # (one way or t'other)

# (Uncomment for debugging:)
##        if allow_event:
##            print 'new value:', new_value
##            if paste: print 'paste'
##            if set_to_none: print 'set_to_none'
##            if set_to_zero: print 'set_to_zero'
##            if set_to_minus_one: print 'set_to_minus_one'
##            if internally_set: print 'internally_set'
##        else:
##            print 'new text:', new_text
##            print 'disallowed'
##        print

        if allow_event:
            if set_to_none:
                CallAfter(ctrl.SetValue, new_value)

            elif set_to_zero:
                # select to "empty" numeric value
                CallAfter(ctrl.SetValue, new_value)
                CallAfter(ctrl.SetSelection, 0, 1)

            elif set_to_minus_one:
                CallAfter(ctrl.SetValue, new_value)
                CallAfter(ctrl.SetSelection, 1, 2)

            elif not internally_set:
                event.Skip()    # allow base TextCtrl to finish processing

        elif not Validator.IsSilent():
            Bell()


class HexCtrl(IntCtrl):
    def __init__(self, *args, **kwargs):
        IntCtrl.__init__(self, *args, **kwargs)
        IntCtrl.SetValidator(self, HexValidator())

    def _toGUI( self, value ):
        # Use _toGUI for bounds / type checking, but discard the
        # str(value) result in favor of our hex(value).
        IntCtrl._toGUI(self, value)
        return "%x" % value

    def _fromGUI( self, value ):
        # Same as IntCtrl's _fromGUI, but with explicit base conversion.
        if value == '':
            return None
        else:
            try:
                return int( value, 16 )
            except ValueError:
                if self.IsLongAllowed():
                    return int( value, 16 )
                else:
                    raise


#===========================================================================

if __name__ == '__main__':

    import traceback

    class myDialog(Dialog):
        def __init__(self, parent, id, title,
            pos = DefaultPosition, size = DefaultSize,
            style = DEFAULT_DIALOG_STYLE ):
            Dialog.__init__(self, parent, id, title, pos, size, style)

            self.int_ctrl = HexCtrl(self, NewId(), limited=1, min=0, max=0x3ff, size=(55,20))
            self.OK = Button( self, ID_OK, "OK")
            self.Cancel = Button( self, ID_CANCEL, "Cancel")

            vs = BoxSizer( VERTICAL )
            vs.AddWindow( self.int_ctrl, 0, ALIGN_CENTRE|ALL, 5 )
            hs = BoxSizer( HORIZONTAL )
            hs.AddWindow( self.OK, 0, ALIGN_CENTRE|ALL, 5 )
            hs.AddWindow( self.Cancel, 0, ALIGN_CENTRE|ALL, 5 )
            vs.AddSizer(hs, 0, ALIGN_CENTRE|ALL, 5 )

            self.SetAutoLayout( true )
            self.SetSizer( vs )
            vs.Fit( self )
            vs.SetSizeHints( self )
            EVT_INT(self, self.int_ctrl.GetId(), self.OnInt)

        def OnInt(self, event):
            print('int now', event.GetValue())

    class TestApp(App):
        def OnInit(self):
            try:
                self.frame = Frame(NULL, -1, "Test",
                                     Point(20,20), Size(120,100)  )
                self.panel = Panel(self.frame, -1)
                button = Button(self.panel, 10, "Push Me",
                                  Point(20, 20))
                EVT_BUTTON(self, 10, self.OnClick)
            except:
                traceback.print_exc()
                return false
            return true

        def OnClick(self, event):
            dlg = myDialog(self.panel, -1, "test IntCtrl")
            dlg.int_ctrl.SetValue(501)
            dlg.int_ctrl.SetSelection(1,2)
            rc = dlg.ShowModal()
            print('final value', dlg.int_ctrl.GetValue())
            del dlg
            self.frame.Destroy()

        def Show(self):
            self.frame.Show(true)

    try:
        app = TestApp(0)
        app.Show()
        app.MainLoop()
    except:
        traceback.print_exc()
