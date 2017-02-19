import pyos


def onStart(s, a):
    tmapp = s.getApplicationList().getApp("task-manager")
    ssapp = s.getApplicationList().getApp("state-shell")
    sinf = open("res/system.json", "rU")
    #inf = pyos.json.loads(str(str(sinf.read(), errors="ignore")))
    inf = pyos.json.loads(sinf.read())    
    sinf.close()
    text = pyos.GUI.MultiLineText((0, 0), """{}, version {}.
Designed and programmed as an open source project by Adam Furman.

Report bugs on GitHub at furmada/PythonOS

Contact the developer: furmada@gmail.com
    """.format(inf.get("name"), str(inf.get("version"))+" beta "+str(inf.get("betaVersion")) if inf.get("beta", False) else str(inf.get("version"))),
     s.getColorPalette().getColor("item"), 14, width=a.ui.width, height=a.ui.height-40)
    btn = pyos.GUI.Button((0, a.ui.height-40), "Start Task Manager", s.getColorPalette().getColor("item"),
                          s.getColorPalette().getColor("background"), width=a.ui.width, height=40,
                          onClick=tmapp.activate)
    btn2 = pyos.GUI.Button((0, a.ui.height-80), "Start State Shell", s.getColorPalette().getColor("background"),
                          s.getColorPalette().getColor("item"), width=a.ui.width, height=40, border=3, borderColor=s.getColorPalette().getColor("item"),
                          onClick=ssapp.activate, onLongClick=pyos.Application.registerDebugAppAsk)
    a.ui.addChild(text)
    a.ui.addChild(btn)
    a.ui.addChild(btn2)
