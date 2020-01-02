#Python 3
"""
    named errorwindow originally
    Import this module into graphical Python apps to provide a
    sys.stderr. No functions to call, just import it. It uses
    only facilities in the Python standard distribution.

    If nothing is ever written to stderr, then the module just
    sits there and stays out of your face. Upon write to stderr,
    it launches a new process, piping it error stream. The new
    process throws up a window showing the error messages.
    
   Code derived from Bryan Olson's source posted in this related Usenet discussion:
   https://groups.google.com/d/msg/comp.lang.python/HWPhLhXKUos/TpFeWxEE9nsJ
   https://groups.google.com/d/msg/comp.lang.python/HWPhLhXKUos/eEHYAl4dH9YJ

   martineau - Modified to use subprocess.Popen instead of the os.popen
               which has been deprecated since Py 2.6. Changed so it
               redirects both stdout and stderr. Also inserted double quotes around paths
               in case they have embedded space characters in them, as
               they did on my Windows system.
               
   to use it with Preview() for openCV player:            
   -changed subprocess.Popen command to list instead of string , so it works under linux
   -added exception to catch window canceled by user and deleting pipe, so new GUI is automatically constructed again if needed,
   -added st.ScrolledText instead of Text
   -made sure that subprocess.Popen executable is python executable (or pythonw under windows),
    under windows, running it from Mystery Keeper's vsedit, sys.executable returned 'vsedit',
"""
import subprocess
import sys
import _thread as thread
import os

ERROR_FILENAME_LOG = 'error_printing_to_gui.txt'

if __name__ == '__main__':  # When spawned as separate process.
    # create window in which to display output
    # then copy stdin to the window until EOF
    # will happen when output is sent to each OutputPipe created
    import tkinter as tk
    import tkinter.scrolledtext as st
    from tkinter import BOTH, END, Frame, TOP, YES
    import tkinter.font as tkFont
    import queue as Queue

    Q_EMPTY = Queue.Empty  # An exception class.
    queue = Queue.Queue(1000)  # FIFO, first put first get

    def read_stdin(app, bufsize=4096):
        while True:
            queue.put(os.read(sys.stdin.fileno(), bufsize)) 

    class Application(Frame):
        def __init__(self, master, font_size=10, family='Courier', text_color='#FFFFFF', rows=3, cols=100):
            super().__init__(master)
            self.master = master
            if len(sys.argv) < 2:
                title = "Output stream from unknown source"
            elif len(sys.argv) < 3: 
                title = "Output stream from {}".format(sys.argv[1])
            else:  # Assume it's a least 3.
                title = "Output stream '{}' from {}".format(sys.argv[2], sys.argv[1])
            self.master.title(title)
            self.pack(fill=BOTH, expand=YES)
            font = tkFont.Font(family=family, size=font_size)
            width = font.measure(' ' * (cols+1))
            height = font.metrics('linespace') * (rows+1)
            self.configure(width=width, height=height)
            self.pack_propagate(0)  # Force frame to be configured size.

            self.logwidget = st.ScrolledText(self, font=font) 
            self.logwidget.pack(side=TOP, fill=BOTH, expand=YES)
            self.logwidget.configure(foreground=text_color)
            self.after(200, self.start_thread, ())  # Start polling thread.

        def start_thread(self, _):
            thread.start_new_thread(read_stdin, (self,))
            self.after(200, self.check_q, ())

        def check_q(self, _):
            go = True
            while go:
                try:
                    data = queue.get_nowait().decode()
                    if not data:
                        data = '[EOF]'
                        go = False
                    self.logwidget.insert(END, data)
                    self.logwidget.see(END)
                except Q_EMPTY:
                    self.after(200, self.check_q, ())
                    go = False
                    
    root = tk.Tk(baseName='whatever_name')
    app = Application(master=root)
    app.mainloop()

else: # when module is first imported
    import traceback

    class OutputPipe(object):
        def __init__(self, name=''):
            self.lock = thread.allocate_lock()
            self.name = name

        def flush(self):  # NO-OP.
            pass

        def __getattr__(self, attr):
            if attr == 'pipe':  # Attribute doesn't exist, so create it.
                # Launch this module as a separate process to display any output it receives
 
                executable = sys.executable                
                try:
                    basename = os.path.basename(executable)
                    name, _ = os.path.splitext(basename)
                    if not name.lower().startswith('python'):
                        executable = self.get_executable()                    
                except:
                    executable = self.get_executable()
                    
                argv1 = __file__
                    
                try:
                    argv2 = os.path.basename(sys.argv[0])
                except:
                    argv2 = ''
                argv3 = self.name
                
                command = [executable]
                for arg in [argv1, argv2, argv3]:
                    if arg:
                        command.append(arg)
                try:
                    # Had to also make stdout and stderr PIPEs too, to work with pythonw.exe
                    self.pipe = subprocess.Popen(command,
                                                 bufsize=0,
                                                 stdin=subprocess.PIPE,
                                                 stdout=subprocess.PIPE,
                                                 stderr=subprocess.PIPE).stdin
                except Exception:
                    # Output exception info to a file since this module isn't working.
                    exc_type, exc_value, exc_traceback = sys.exc_info()
                    msg = '{} exception in {}\n'.format(exc_type.__name__, os.path.basename(__file__))
                    with open(ERROR_FILENAME_LOG, 'wt') as info:
                        info.write('fatal error occurred spawning output process')
                        info.write('exeception info:' + msg)
                        traceback.print_exc(file=info)

                    sys.exit('fatal error occurred')

            return super(OutputPipe, self).__getattribute__(attr)
        
        def get_executable(self):
            #if running this within vsedit under windows sys.executable name is 'vsedit'
            return 'pythonw'
            
        def write(self, data):
            with self.lock:
                try:
                    data = data.encode()
                    self.pipe.write(data)  # First reference to pipe attr will cause an
                                           # OutputPipe process for the stream to be created.                                      
                except Exception:
                    #gui was canceled by user, piping would cause error
                    #pipe attr can be deleted so new is constructed with __getattr__() and therefore new GUI pops up if needed
                    del self.pipe
                    #pass

    try:
        os.remove(EXC_INFO_FILENAME)  # Delete previous file, if any.
    except Exception:
        pass

    # Redirect standard output streams in the process that imported this module.
    sys.stderr = OutputPipe('stderr')
    sys.stdout = OutputPipe('stdout')