import pcbnew
import os.path
import re
import place_by_sch.sch as sch

def PlaceBySch():
    board = pcbnew.GetBoard()

    board_path = board.GetFileName()
    sch_path = board_path.replace(".kicad_pcb", ".sch")

    if (not os.path.isfile(sch_path)):
        raise ValueError("file {} doesn't exist".format(sch_path))

    locs = sch.get_locations(sch_path)
    print(locs)
    
    for mod in board.GetModules():
        ref = mod.GetReference()
        if (str(ref) not in locs):
            print("couldn't get loc info for {}".format(ref))
            continue
        ref = str(ref)
        # eeschema stores stuff in 1000ths of an inch.
        # pcbnew stores in 10e-6mm
        # 1000ths inch * inch/1000ths inch * 25.4mm/inch * 10e6
        # oldvalue * 25.4 / 10e4
        newx = int(locs[ref]["pos"]["posx"]) * 25.4 * 1000.0
        newy = int(locs[ref]["pos"]["posy"]) * 25.4 * 1000.0
        mod.SetPosition(pcbnew.wxPoint(int(newx), int(newy)))
        mod.SetOrientation(locs[ref]["degree"]*10)
        print("placing {} at {},{}".format(ref, newx, newy))

    # when running as a plugin, this isn't needed. it's done for you
    #pcbnew.Refresh();

class PlaceBySchPlugin(pcbnew.ActionPlugin):
    def defaults(self):
        self.name = "Place By Sch"
        self.category = "A descriptive category name"
        self.description = "This plugin reads the .sch file and apply its placements to the current design"

    def Run(self):
        # The entry function of the plugin that is executed on user action
        PlaceBySch()


PlaceBySchPlugin().register() # Instantiate and register to Pcbnew