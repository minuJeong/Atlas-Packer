# crawl job module
# author: Minu Jeong

# internal libraries
import os, glob, json
import time


# external libraires
from PIL import Image, ImageTk
from psd_tools import *
import imagehash # numpy/scipy required

# for further update
import mechanize # Virtual browsing library
from bs4 import BeautifulSoup # html parser


class PSDDealer:
	""" Read psd files from configured local directory, save as png files.
	Includes image hashing to prevent rewrite over and over. 
	Note, "conf.json" file should be configured. """

	def __init__(self, app):
		""" initialize job """

		print "[=] initializing psd worker"

		self.stop = False
		self.apphandler = app
		pass


	def askrun(self, iterate=0):
		""" workflow starts here. """

		if iterate == 0:
			self.stop = True

		# read configures
		self.load_config()

		# read psd files
		for f in glob.glob(self.conf["psd_handler"]["src_dir_psd"] + "/*"):
			if f[f.find("."):] == ".psd":
				self.process_psd(f)


		# terminate thread
		if self.stop:
			print "[!!] thread complete"
			if self.apphandler.bool_packtexture.get() != 0:
				packer = TextureDealer(self.apphandler)
				packer.askrun()
			else:
				self.apphandler.onWorkTerminate()
			return


		# time: 
		time.sleep(self.conf["psd_handler"]["frequency"]/1000)
		self.askrun(1)
		pass

	def askstop(self):
		self.stop = True
		pass


	def load_config(self):
		""" load/read conf file """

		conf_file = open("conf.json")
		self.conf = json.loads(conf_file.read())
		pass


	def process_psd(self, file_path):
		""" do what you want here. """

		# read psd file
		psd = PSDImage.load(file_path)

		# create directory for each psd file
		png_dir_path = "%s/__%s__.gen"%(self.conf["psd_handler"]["src_dir_psd"], os.path.basename(file_path)[:-4])
		
		if not os.path.exists(png_dir_path):
			os.makedirs(png_dir_path)

		data = {}


		# layer processing block
		def process_layer(layer):
			""" save layer as png file, and record x, y, width, height as json file. """

			try :
				layer_image = layer.as_PIL()
			except :
				# Frequent problem: layer is empty.
				print "[!] layer as pil failed. Check if layer is not empty. Empty layer cannot saved as png file."

			# remove colon from layer name
			n = layer.name.replace(": ", "_")

			png_file_name = "%s/%s.png"%(png_dir_path, n)

			if os.path.isfile(png_file_name):
				if imagehash.average_hash(Image.open(png_file_name)) == imagehash.average_hash(layer_image):
					print "[-] layer not changed: %s"%(layer.name)
					return
			
			layer_image.save(png_file_name)


			# save as: __data__.json
			data[n] = {}
			data[n]['x'] = layer.bbox.x1
			data[n]['y'] = layer.bbox.y1

			data[n]['size'] = {}
			data[n]['size']['width'] = layer.bbox.width
			data[n]['size']['height'] = layer.bbox.height
			pass

		
		for layer in psd.layers:
			if type(layer) == Group:
				""" TODO: support for layer group """
				print "[!] group processing is not supported."
				pass

			process_layer(layer)
			pass


		# save as file.
		f_data = open("%s/__data__.json"%(png_dir_path), "w")
		f_data.write(json.dumps(data, indent=4))
		f_data.close()
		pass


class TextureDealer:
	""" Creates texture atlas from png files generated from psd dealer class.
	After atlas created, send atlas to Unity Project directory.
	Require proper configuration at "conf.json" file. """

	def __init__(self, app):
		""" docstring for TextureDealer init. None written. """

		print "[=] initializing texture worker"

		self.apphandler = app
		self.stop = False
		pass


	def askrun(self, iterate=0):
		""" workflow starts here. """

		# read configures
		conf_file = open("conf.json")
		self.conf = json.loads(conf_file.read())

		self.process_texture()

		self.apphandler.onWorkTerminate()
		pass

	def askstop(self):
		self.stop = True
		pass

	def process_texture(self):
		""" gather images, start packing algorithm"""
		
		# grab images from directories.
		image_dirs = []

		folders = glob.glob("%s/*"%self.conf["psd_handler"]["src_dir_psd"])
		for folder in folders:
			if not os.path.isdir(folder):
				# filter directories
				continue

			for f in glob.glob("%s/*.png"%(folder)):
				image_dirs.append(f)
				pass
			pass
		
		# gather opened images from paths
		images = [(os.path.basename(image_dir)[:-4], Image.open(image_dir)) for image_dir in image_dirs]

		# sort list by width * height
		images = sorted(images, key=lambda (name, image): image.size[0] * image.size[1]) # from small to big
		images.reverse() # from big to small
		
		# temp class definition
		class Node:
			
			x = property(fget=lambda self: self.area[0])
			y = property(fget=lambda self: self.area[1])
			x_edge = property(fget=lambda self: self.area[2])
			y_edge = property(fget=lambda self: self.area[3])
			width = property(fget=lambda self: self.x_edge - self.x)
			height = property(fget=lambda self: self.y_edge - self.y)

			def __init__(self, area):
				if len(area) == 2:
					area = (0,0,area[0],area[1])
				self.area = area
				pass

			def insert(self, area):
				# go down to child
				if hasattr(self, 'child'):
					a = self.child[0].insert(area)
					if a is None:
						a = self.child[1].insert(area)
					return a

				# is image fit to area
				image_area = Node(area)
				if image_area.width <= self.width and image_area.height <= self.height:
					self.child = [None, None]
					self.child[0] = Node((self.x + image_area.width, self.y,
										 self.x_edge, self.y + image_area.height))
					self.child[1] = Node((self.x, self.y + image_area.height,
										 self.x_edge, self.y_edge))

					return Node((self.x, self.y, self.x + image_area.width, self.y + image_area.height))

			pass # end of class Node

		pack_size = (self.conf["psd_handler"]["texture_size"]["width"], self.conf["psd_handler"]["texture_size"]["height"])
		tree = Node(pack_size)

		data = {}

		image = Image.new('RGBA', pack_size)
		for name, img in images:
			uv = tree.insert(img.size)
			if uv is None:
				# no child left
				raise ValueError("Pack Size too small.")
			image.paste(img, uv.area)
			
			data[name] = {}
			data[name]["x"] = uv.x
			data[name]["y"] = uv.y
			data[name]["width"] = uv.width
			data[name]["height"] = uv.height

		if not os.path.exists(self.conf["psd_handler"]["trg_dir"]):
			os.makedirs(self.conf["psd_handler"]["trg_dir"])
		image.save("%s/textureAtlas.png"%(self.conf["psd_handler"]["trg_dir"]), "PNG")
		open("%s/atlas_data.json"%(self.conf["psd_handler"]["trg_dir"]), "w").write(json.dumps(data, indent=4))
		


if __name__ == "__main__":
	""" TODO: delete these code block: under if __main__ state """
	""" used for debug purpose only """
	import app
	app.run()