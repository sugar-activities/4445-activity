// to keep things simple, follow the same format
// latitude: North of equator = positive, South of equator = negative
// longitude: East of prime meridian = positive, West of prime meridian = negative
// north and west: use coordinates of top left corner
// east: use longitude coordinate of eastern border -- used to find scalable width of the map
// mapCode can be tricky to work out:
//		0 for the one base map (a map of the whole country)
//		1 to 5 are the overlay maps.  A 2 overlaps a 1, a 3 overlaps both 2 and 1, and so on
//		try not to have maps with the same mapCode near each other.  You cannot see two "3" maps at the same time.
//		mapCode exists because the activity slows down *extremely* with more than 5 overlay maps moving at the same time
maps=[
	{link:"uy-sat-map.jpg",title:"Uruguay con pa&iacute;ses lim&iacute;trofes (NASA Blue Marble)",north:-29.2560944,east:-52.0225194,west:-59.6770306,south:-35-0.25-59.01/60/60,mapCode:0,showZoom:1,checkID:null},
	{link:"uy-road-basemap.png",title:"Uruguay (OSM rutas)",north:-29-56/60-1.12/60/60,east:-53-1/60-19.09/60/60,west:-59-11/60,south:-35-39.08/60/60,mapCode:1,showZoom:1,checkID:null},
	{link:"uy-mvd-road-detail.png",title:"Montevideo (OSM rutas)",north:-34-46/60-38.77/60/60,east:-55-56/60-56.59/60/60,west:-56-18/60-59.57/60/60,south:-34-55/60-51.34/60/60,mapCode:2,showZoom:16,checkID:null},
	{link:"-road-FrayBentos.jpg",title:"Fray Bentos (Servicio Geografico Militar - rutas y parques)",north:-33-0.1-33.25/60/60,west:-58-19/60-54.74/60/60,east:-58-0.25-49.84/60/60,south:null,mapCode:2,showZoom:18,checkID:null},
	{link:"Colonia-road-detail.jpg",title:"Colonia del Sacramento (Servicio Geografico Militar y NASA Blue Marble)",north:-34-24/60-36.06/60/60,west:-57-53/60-47.16/60/60,east:-57-47/60-59.18/60/60,south:-34-29/60-2.92/60/60,mapCode:3,showZoom:18,checkID:null},
	{link:"artigas-road-map.jpg",title:"Artigas (OSM rutas)",north:-30-22/60-56.99/60/60,west:-56-0.5-52.53/60/60,east:-56-25/60-48.03/60/60,south:-30-25/60-34.64/60/60,mapCode:3,showZoom:16,checkID:null},
	{link:"canelones-road-map.jpg",title:"Canelones (OSM rutas)",north:-34-0.5-20.36/60/60,west:-56-18/60-56.79/60/60,east:-56-14/60-8.83/60/60,south:-34-32/60-45.09/60/60,mapCode:4,showZoom:16,checkID:null},
	{link:"melo-sat-map.jpg",title:"Melo (NASA LandSat)",north:-32-20/60-2.72/60/60,west:-54-0.2-51.34/60/60,east:-54-4/60-50.93/60/60,south:-32-25/60-5.57/60/60,mapCode:3,showZoom:17,checkID:null},
	{link:"melo-road-map.jpg",title:"Melo (Servicio Geografico Militar - rutas)",north:-32-20/60-26.79/60/60,west:-54-0.2-44.89/60/60,east:-54-0.1-38.85/60/60,south:-32-23/60-47.29/60/60,mapCode:4,showZoom:17,checkID:null},
	{link:"trinidad-sat-map.jpg",title:"Trinidad (NASA LandSat)",north:-33-27/60-3.76/60/60,west:-57-1/60-10.38/60/60,east:-56-47/60-42.21/60/60,south:-33-35/60-8.93/60/60,mapCode:3,showZoom:17,checkID:null},
	{link:"trinidad-road-map.jpg",title:"Trinidad (Servicio Geografico Militar - rutas)",north:-33-29/60-36.68/60/60,west:-56-57/60-19.74/60/60,east:-56-50/60-33.36/60/60,south:-33-33/60-13.36/60/60,mapCode:4,showZoom:17,checkID:null},
	{link:"florida-sat-map.jpg",title:"Florida (NASA LandSat)",north:-33-56/60-56.33/60/60,west:-56-20/60-17.54/60/60,east:-56-5/60-37.49/60/60,south:-34-0.2-28.07/60/60,mapCode:3,showZoom:15,checkID:null},
	{link:"minas-road-map.jpg",title:"Minas (Servicio Geografico Militar - rutas)",north:-34-19/60-32.24/60/60,west:-55-17/60-55.63/60/60,east:-55-8/60-35.44/60/60,south:-34-24/60-32.88/60/60,mapCode:4,showZoom:17,checkID:null},
	{link:"puntadeleste-sat-map.jpg",title:"Maldonado (NASA LandSat)",north:-34-49/60-14.57/60/60,west:-55-4/60-40/60/60,east:-54-49/60-1.53/60/60,south:-34-58/60-57.10/60/60,mapCode:3,showZoom:17,checkID:null},
	{link:"puntadeleste-road-sinisla.jpg",title:"Punta del Este (OSM rutas)",north:-34-53/60-44.76/60/60,west:-54-57/60-50.83/60/60,east:-54-53/60-20.54/60/60,south:-34-58/60-26.43/60/60,mapCode:4,showZoom:17,checkID:null},
	{link:"rivera-sat-map.jpg",title:"Rivera (NASA LandSat)",north:-30-49/60-47.94/60/60,west:-55-40/60-9.70/60/60,east:-55-23/60-46.1/60/60,south:-30-59/60-55.75/60/60,mapCode:4,showZoom:17,checkID:null},
	{link:"rivera-road-map.jpg",title:"Rivera (Servicio Geografico Militar - rutas)",north:-30-51/60-59/60/60,west:-55-37/60-29.22/60/60,east:-55-28/60-42.51/60/60,south:-30-57/60-19/60/60,mapCode:5,showZoom:17,checkID:null},
	{link:"salto-sat-map.jpg",title:"Salto (NASA LandSat)",north:-31-0.25-11.64/60/60,west:-58-29.59/60/60,east:-57-0.75-16.85/60/60,south:-31-25/60-39.16/60/60,mapCode:2,showZoom:17,checkID:null},
	{link:"salto-road-map.jpg",title:"Salto (OSM - rutas)",north:-31-21/60-3.09/60/60,west:-58-32.12/60/60,east:-57-53/60-0.04/60/60,south:-31-26/60-3.82/60/60,mapCode:3,showZoom:17,checkID:null},
	{link:"sanjose-road-map.jpg",title:"San Jos&eacute; de Mayo (Servicio Geografico Militar - rutas)",north:-34-18/60-40.73/60/60,west:-56-44/60-58.34/60/60,east:-56-40/60-13.95/60/60,south:-34-21/60-25.24/60/60,mapCode:3,showZoom:17,checkID:null},
	{link:"mercedes-road-map.jpg",title:"Mercedes (Servicio Geografico Militar - rutas)",north:-33-0.2-18.99/60/60,west:-58-5/60-39.22/60/60,east:-57-58/60-26.71/60/60,south:-33-16/60-15.58/60/60,mapCode:3,showZoom:17,checkID:null},
	{link:"treintaytres-sat-map.jpg",title:"Treinta y Tres (NASA LandSat)",north:-33-7/60-57.26/60/60,west:-54-0.5-29.36/60/60,east:-54-0.25-22.9/60/60,south:-33-17/60-34.03/60/60,mapCode:4,showZoom:17,checkID:null},
	{link:"treintaytres-road-map.jpg",title:"Treinta y Tres (Servicio Geografico Militar - rutas)",north:-33-0.2-44.37/60/60,west:-54-25/60-54.84/60/60,east:-54-21/60-27.83/60/60,mapCode:5,showZoom:17,checkID:null},
	{link:"Paysandu-road-detail.jpg",title:"Paysand&uacute; (Servicio Geografico Militar)",north:-32-15/60-23/60/60,west:-58-0.1-32.18/60/60,east:-58-2/60-6.83/60/60,south:null,mapCode:4,showZoom:17,checkID:null},
	{link:"-road-PasoDeLosToros.jpg",title:"Paso de los Toros (Servicio Geografico Militar)",north:-32-47/60-46.56/60/60,west:-56-32/60-51.75/60/60,east:-56-28/60-50.95/60/60,south:-32-49/60-36.98/60/60,mapCode:4,showZoom:16},
	{link:"-road-Tacuarembo.jpg",title:"Tacuaremb&oacute; (Servicio Geografico Militar)",north:-31-40/60-42.68/60/60,west:-56-2/60-7.11/60/60,east:-55-55/60-29.27/60/60,south:-31-44/60-2.34/60/60,mapCode:5,showZoom:16},
	{link:"durazno-road-map.jpg",title:"Durazno (OSM rutas)",north:-33-21/60-18.43/60/60,west:-56-34/60-0.78/60/60,east:-56-28/60-37.66/60/60,south:-33-23/60-59.53/60/60,mapCode:5,showZoom:16},
	{link:"durazno-sat-map.jpg",title:"Durazno (NASA World Wind)",north:-33-17/60-52.2/60/60,west:-56-38/60-39.52/60/60,east:-56-23/60-16.17/60/60,south:-33-27/60-8.84/60/60,mapCode:4,showZoom:16},
	{link:"-sat-Rocha-Paloma-Polonio.jpg",title:"Rocha, La Paloma, La Pedrera, y Cabo Polonio (NASA Blue Marble)",north:-34-13/60-53.29/60/60,east:-53-44/60-18.9/60/60,west:-54-23/60-57.09/60/60,south:-34-40/60-34.08/60/60,mapCode:5,showZoom:15,checkID:null}
];

// this name only appears on the library view in Browse
countryName="Uruguay";

// these values vary depending on how far you are from the equator
// tweak these if latitudes and longitudes seem to vary at the wrong rate across your base map
latFactor=120.000;
lngFactor=103.000;
