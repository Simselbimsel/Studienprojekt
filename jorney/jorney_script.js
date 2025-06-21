const { createClient } = require('db-vendo-client');
const { profile: dbnav } = require('db-vendo-client/p/dbnav/index.js');
const fs = require('fs');
const path = require('path');

const client = createClient(dbnav, 'mein-bahn-test');

// Argumente robust lesen
const args = process.argv.slice(2);
const fromName = args[0] || 'Berlin Hbf';
const toName = args[1] || 'München Hbf';

console.log(`🔍 Starte Suche von "${fromName}" nach "${toName}"`);

const getStation = async (name) => {
  const results = await client.locations(name, { results: 1 });
  if (!results || results.length === 0 || !results[0].id) {
    throw new Error(`Bahnhof "${name}" nicht gefunden`);
  }
  return results[0];
};

const saveToFile = (data, filename = 'output/journeys.json') => {
  const dir = path.dirname(filename);
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(filename, JSON.stringify(data, null, 2), 'utf-8');
  console.log(`✅ Datei gespeichert: ${filename}`);
};


const getDurationInMinutes = (journey) => {
  try {
    const departure = new Date(journey.legs[0].departure);
    const arrival = new Date(journey.legs[journey.legs.length - 1].arrival);
    return (arrival - departure) / 60000; // Minuten
  } catch {
    return Infinity;
  }
};

const getDurationFormatted = (journey) => {
  try {
    const departure = new Date(journey.legs[0].departure);
    const arrival = new Date(journey.legs[journey.legs.length - 1].arrival);
    const diffMs = arrival - departure;

    const totalMinutes = Math.floor(diffMs / 60000);
    const hours = Math.floor(totalMinutes / 60);
    const minutes = totalMinutes % 60;

    // Formatieren mit führender Null bei Minuten < 10
    return `${hours}:${minutes.toString().padStart(2, '0')}`;
  } catch {
    return '?:??';
  }
};




const formatTime = (isoString) => {
  if (!isoString) return '?';
  const date = new Date(isoString);
  return new Intl.DateTimeFormat('de-DE', {
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  }).format(date);
};



const main = async () => {
  try {
    const from = await getStation(fromName);
    const to = await getStation(toName);

    const { journeys } = await client.journeys(from, to, {
      results: 10,
      stopovers: true,
      remarks: true,
	  polylines: false,
      scheduledDays: true
    });
	
	
	

    if (!journeys || journeys.length === 0) {
      throw new Error('no connection');
    }
	
	
    // Nach Fahrzeit sortieren (kürzeste zuerst)
    journeys.sort((a, b) => getDurationInMinutes(a) - getDurationInMinutes(b));
	
	// Enrichment: jede Zwischenstation extrahieren
    const enriched = [];

	journeys.forEach((journey, index) => {
      journey.legs.forEach((leg) => {
        if (!leg.stopovers) return;

        leg.stopovers.forEach((stop) => {
          enriched.push({
            journey_number: index + 1,
            from: journey.legs[0]?.origin?.name,
            to: journey.legs[journey.legs.length - 1]?.destination?.name,
            departure: formatTime(leg.departure),
            arrival: formatTime(leg.arrival),
            duration: getDurationFormatted(journey),
            train: leg.line?.name,
            train_type: leg.line?.product,
            mode: leg.mode,
            direction: leg.direction,
            stop_name: stop.stop?.name,
            stop_arrival: formatTime(stop.arrival),
            stop_departure: formatTime(stop.departure),
            occupancy: stop.occupancy?.secondClass || null,
			      loadFactor: leg.loadFactor || null,
          });
        });
      });
    });

    saveToFile(enriched, 'jorney/output/journeys.json');



    // saveToFile(journeys, 'output/journeys.json');
  } catch (err) {
    console.error('❌ Fehler:', err.message);
    process.exit(1);
  }
};

main();
