DATAFILES = $(basename $(wildcard data/*.xz))

all: $(DATAFILES)

data/%: data/%.xz
	unxz -k $<
