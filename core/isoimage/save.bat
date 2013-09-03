java -Xms512M -Xmx1024M -cp minecraft-server.jar; OrigFormat save %1 server_level.dat
javaw -Xms128M -Xmx1024M -cp isocraft++.jar;minecraft-server.jar isocraft server_level.dat tileset.png output.png %3 -1 -1 -1 -1 -1 -1 visible
move /Y output.png images\%2%3.png