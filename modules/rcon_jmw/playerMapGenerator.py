import json
import os
from os import listdir
from os.path import isfile, join
import numpy as np
import numpy.random

from PIL import Image, ImageDraw
import  matplotlib.cm
import sys
import io
from scipy.ndimage.filters import gaussian_filter
from scipy import misc
# Usage: img = generateMap(self, player_name="all", bins=50)

class playerMapGenerator():
    def __init__(self, path):
        self.MAP_SIZE = 30720
        self.data_path = path
        self.path = os.path.dirname(os.path.realpath(__file__))
        self.color = matplotlib.cm.get_cmap('jet')
        
    def getPlayers(self, data, player_name="all"):
        p = []
        if(not "players" in data):
            return []
        players = data["players"]
        for player in players:
            if(player_name != "all" and player[0]!=player_name):
                continue
            
            if(player[3][0] >= 0 and player[3][0] <= self.MAP_SIZE and player[3][1] >= 0 and player[3][1] <= self.MAP_SIZE):
                p.append([player[3][0],player[3][1]])
            
            #if(player[3][0] > 50000 or player[3][1] > 50000):
            #    print(player)
        return p

    def generateData(self, player_name="all"):
        files = [f for f in listdir(self.data_path) if isfile(join(self.data_path, f))]

        players=[] #[[0,0],[self.MAP_SIZE,self.MAP_SIZE]]  
        for file in files:
            if("CUR" not in file and "ADV" in file and "Altis" in file):
                with open(self.data_path+"/"+file) as f:
                    data = json.load(f)
                    if(len(data) > 0):
                        for row in data:
                            if(row["CTI_DataPacket"] == "Data"):
                                players += self.getPlayers(row, player_name)
        return np.array(players)

    def drawheatmap(self, data, img):
        color = (0, 0, 0)  # Black
        TRANSPARENCY = .4  # Degree of transparency, 0-100%
        OPACITY = int(255 * TRANSPARENCY)
        
        data = np.rot90(data)
        max = data.max()
        overlay = Image.new('RGBA', img.size, color+(0,))
        draw = ImageDraw.Draw(overlay)  # Create a context for drawing things on it.
        height = img.size[0]
        width  = img.size[1]
        bins = len(data)
        
        x_size = int(height/bins)
        y_size = int(width/bins)
        for y,row in enumerate(data):
            for x,val in enumerate(row):
                color = self.colvF1(val, max)
                
                x_pos = int(x_size * x)
                y_pos = int(y_size * y)
                if(not (color[0] == 0 and color[1] == 0 and color[2] == 0)):
                    #draw.putpixel((30,60), (155,155,55))
                    draw.rectangle(((x_pos, y_pos),(x_pos + x_size, y_pos + y_size)), fill=color+(OPACITY,))

        # Alpha composite these two imgs together to obtain the desired result.
        img = Image.alpha_composite(img, overlay)
        img = img.convert("RGB")
        return img

    def colvF1(self, val, max=10):
        norm = val / max
        rgba = self.color(norm)
        #if(val == 0):
        #    return (0,0,0)
        return (round(int(256*rgba[0])), round(int(256*rgba[1])), round(int(256*rgba[2])))


        
    def generateMap(self, player_name="all", bins=1000, sigma=16, new=False):
        img = Image.open(self.path+'/mapTemplates/Altis_sat_s.jpg').convert('LA').convert("RGBA")
        players = self.generateData(player_name)
        print("Cords Count:", len(players))
        if(len(players) == 0):
            return False

        # Generate data
        x = players[:,0]
        y = players[:,1]

        heatmapD, xedges, yedges = np.histogram2d(x, y, bins=bins, range=[[0,self.MAP_SIZE],[0,self.MAP_SIZE]])
        if(new):
            heatmapD = gaussian_filter(heatmapD, sigma=sigma)
        img = self.drawheatmap(heatmapD, img)
        #return img
        byteImgIO = io.BytesIO()
        img.save(byteImgIO, "JPEG")
        byteImgIO.seek(0)
        
        return byteImgIO

# d = playerMapGenerator("data/")
# img = d.generateMap("all", 1000)
# img = img.convert("RGB")
# img.save('test.jpg')