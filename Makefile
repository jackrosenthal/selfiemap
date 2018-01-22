DATAFILES = $(basename $(wildcard data/*.xz))
MAPFILES = $(patsubst %,data/world.topo.bathy.200401.3x%.png, 21600x10800) data/world16384.png

all: $(DATAFILES) $(MAPFILES)

data/%.csv: data/%.csv.xz
	unxz -k $<

data/world.topo.bathy.%.png:
	wget https://eoimages.gsfc.nasa.gov/images/imagerecords/73000/73580/$(notdir $@) -O $@

data/world16384.png: data/world.topo.bathy.200401.3x21600x10800.png
	convert $< -resize 16384x $@
