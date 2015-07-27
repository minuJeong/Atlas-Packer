# Asset Manager Application wrapped in Tkinter
# author: Minu Jeong


# python internal libraries
import threading
import json

from Tkinter import *


# python external libraires

# project modules
from job import *


# App Class Definition
class App:

    """ GUI application wrapping """

    def __init__(self, master):

        #
        self.master = master

        # workers
        self.psddealer = PSDDealer(self)
        self.texturedealer = TextureDealer(self)

        # read configuration file
        conf = json.loads(open("conf.json").read())
        self.window_width = conf["window_width"]
        self.window_height = conf["window_height"]
        self.master.minsize(self.window_width, self.window_height)
        self.master.maxsize(self.window_width, self.window_height)

        # GUI elements
        self.frame_button = Frame(master)
        self.frame_button.pack(side=TOP)

        self.frame_checkbutton = Frame(master)
        self.frame_checkbutton.pack(side=TOP)

        self.bool_repeat = IntVar()
        self.cb_repeatrun = Checkbutton(
            self.frame_checkbutton, text="Repeat parsing psd files. [r]", variable=self.bool_repeat)
        self.cb_repeatrun.pack(side=BOTTOM)

        self.bool_packtexture = IntVar()
        self.cb_createtexture = Checkbutton(
            self.frame_checkbutton, text="Generate atlas texture. [t]", variable=self.bool_packtexture)
        self.cb_createtexture.pack(side=BOTTOM)

        self.b_run = Button(self.frame_button, text="Loading")
        self.b_run.pack(side=TOP, expand=YES, fill=Y)

        # terminate handler
        self.b_quit = Button(
            self.frame_button, text="Exit", command=self.onQuit)
        self.master.bind("<Command-q>", self.onQuit)
        self.master.bind("<Command-w>", self.onQuit)
        self.master.bind("<Escape>", self.onQuit)
        self.b_quit.pack(side=TOP, expand=YES, fill=Y)

        # start listening buttons
        self.enableRunButton()
        pass

    # toggle button
    def enableRunButton(self):
        self.b_run["text"] = "Run"
        self.b_run["command"] = self.onRun
        self.master.bind("<space>", self.onRun)
        self.cb_repeatrun.configure(state="normal")
        self.cb_createtexture.configure(state="normal")
        self.master.bind("r", self.onRepeatToggle)
        self.master.bind("t", self.onTexturePackToggle)
        pass

    def disableRunButton(self):
        self.b_run["text"] = "Stop"
        self.b_run["command"] = self.onStop
        self.master.bind("<space>", self.onStop)
        self.cb_repeatrun.configure(state="disabled")
        self.cb_createtexture.configure(state="disabled")
        self.master.unbind("r")
        self.master.unbind("t")
        pass

    # Button click event handlers
    def onRun(self, event=None):
        self.disableRunButton()

        t_PSDDealer = threading.Thread(target=self.onThreadStarted_PSDDealer)
        t_PSDDealer.start()
        pass

    def onStop(self, event=None):
        self.enableRunButton()
        self.psddealer.askstop()
        pass

    def onQuit(self, event=None):
        self.onStop()
        self.master.quit()
        pass

    def onRepeatToggle(self, event=None):
        self.cb_repeatrun.toggle()
        pass

    def onTexturePackToggle(self, event=None):
        self.cb_createtexture.toggle()
        pass

    # psd dealer thread
    def onThreadStarted_PSDDealer(self):
        self.psddealer.askrun(self.bool_repeat.get())
        pass

    # event handler
    def onWorkTerminate(self):
        self.onStop()
        pass


def run():
    """ start point of this project. """

    master = Tk()
    master.wm_title("GUIed Asset Manager")

    app = App(master)
    master.mainloop()


if __name__ == "__main__":
    run()
