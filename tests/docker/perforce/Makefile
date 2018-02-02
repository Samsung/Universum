.PHONY: all

all: test_run

test_run:
	docker run -d -e SERVER_NAME=perforce -e P4PASSWD=abcd123efg -p 1667:1666 --name=perforce perforce 
