#Python 3
"""
Graphical Print Hook, allows you to redirect stdout and stderr
to a seperate graphical window. Particularly useful for software
with no logging (or printing) support.
Simply `import printhook` and it will redirect as necessary.
New GUI process will only be created once data is sent to stdout
or stderr.

Created by Bryan Olsen:
https://groups.google.com/d/msg/comp.lang.python/HWPhLhXKUos/TpFeWxEE9nsJ

Modifications:
- [Change]:   Replaced `Text` with `st.ScrolledText` [@martineau]
- [Change]:   Replaced `os.popen` with `subprocess.Popen` (`os.popen` is deprecated) [@martineau]
- [Change]:   Redirects both `stdout` and `stderr` [@martineau]
- [Change]:   Replaced `subprocess.Popen`'s command to a `list` instead of `string` (linux support) [@martineau]
- [Addition]: Inserted double quotes around paths in case they have embedded space characters [@martineau]
- [Addition]: Added exception to catch window canceled by user and deleting pipe [@martineau]
- [Cleanup]:  Cleaned up the entire codebase, removed unnecessary whitespace, fixed indentation, e.t.c [@rlaPHOENiX]
"""
import subprocess
import sys
import _thread as thread
import os

if __name__ == '__main__':
    # When spawned as separate process.
    # create window in which to display output
    # then copy stdin to the window until EOF
    # will happen when output is sent to each OutputPipe created
    import tkinter as tk
    import tkinter.scrolledtext as st
    from tkinter import BOTH, END, Frame, TOP, YES
    import tkinter.font as tkFont
    import queue as Queue

    queue = Queue.Queue(1000)  # FIFO, first put first get

    class Application(Frame):

        def __init__(self, master, font_size=10, family="Courier", text_color="#FFFFFF", rows=3, cols=100):
            super().__init__(master)
            self.master = master
            if len(sys.argv) < 2:
                title = "Output stream from unknown source"
            elif len(sys.argv) < 3:
                title = f"Output stream from {sys.argv[1]}"
            else:  # Assume it's a least 3.
                title = f"Output stream '{sys.argv[2]}' from {sys.argv[1]}"
            self.master.title(title)
            self.pack(fill=BOTH, expand=YES)
            font = tkFont.Font(family=family, size=font_size)
            self.configure(
                width=font.measure(" " * (cols+1)),
                height=font.metrics("linespace") * (rows+1)
            )
            # Force frame to be configured size.
            self.pack_propagate(0)
            self.logwidget = st.ScrolledText(self, font=font)
            self.logwidget.pack(side=TOP, fill=BOTH, expand=YES)
            self.logwidget.configure(foreground=text_color)
            # Start polling thread.
            self.after(200, self.start_thread, ())

        def start_thread(self, _):
            def read_stdin(app, bufsize=4096):
                while True:
                    queue.put(os.read(sys.stdin.fileno(), bufsize))
            thread.start_new_thread(read_stdin, (self,))
            self.after(200, self.check_q, ())

        def check_q(self, _):
            go = True
            while go:
                try:
                    data = queue.get_nowait().decode()
                    if not data:
                        data = "[EOF]"
                        go = False
                    self.logwidget.insert(END, data)
                    self.logwidget.see(END)
                except Queue.Empty:
                    self.after(200, self.check_q, ())
                    go = False

    root = tk.Tk(baseName='pvsfunc - printhook')
    app = Application(master=root)
    app.mainloop()
else:
    # when module is first imported
    class OutputPipe(object):
        def __init__(self, name=""):
            self.lock = thread.allocate_lock()
            self.name = name

        def flush(self):  # NO-OP.
            pass

        def __getattr__(self, attr):
            if attr == "pipe":
                # Attribute doesn't exist, so create it.
                # Launch this module as a separate process to display any output it receives
                executable = sys.executable
                try:
                    basename = os.path.basename(executable)
                    name, _ = os.path.splitext(basename)
                    if not name.lower().startswith("python"):
                        executable = self.get_executable()
                except:
                    executable = self.get_executable()
                try:
                    # Had to also make stdout and stderr PIPEs too, to work with pythonw.exe
                    self.pipe = subprocess.Popen(
                        [
                            executable,
                            __file__,
                            os.path.basename(sys.argv[0]) if len(sys.argv) > 0 else "",
                            self.name
                        ],
                        bufsize=0,
                        stdin=subprocess.PIPE,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE
                    ).stdin
                except:
                    sys.exit("fatal error occurred")
            return super(OutputPipe, self).__getattribute__(attr)

        def get_executable(self):
            return "pythonw"  # when using vsedit on windows, sys.executable is "vsedit"

        def write(self, data):
            with self.lock:
                try:
                    # First reference to pipe attr will cause an
                    # OutputPipe process for the stream to be created.
                    self.pipe.write(data.encode())
                except Exception:
                    # gui was canceled by user, piping would cause error
                    # pipe attr can be deleted so new is constructed with __getattr__() and therefore new GUI pops up if needed
                    del self.pipe

    # Redirect standard output streams in the process that imported this module.
    sys.stderr = OutputPipe("stderr")
    sys.stdout = OutputPipe("stdout")
