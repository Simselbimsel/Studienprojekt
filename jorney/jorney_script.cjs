const { createClient } = require('db-vendo-client');
const { profile: dbnav } = require('db-vendo-client/p/dbnav/index.js');
const fs = require('fs');
const path = require('path');

const client = createClient(dbnav, 'mein-bahn-test');

// Parameter einlesen und default setzen
const args = process.argv.slice(2);
const fromName = args[0] || 'Berlin Hbf';
const toName = args[1] || 'München Hbf';

// holt uns Stationsdaten
const getStation = async (name) => {
  const results = await client.locations(name, { results: 1 });
  if (!results || results.length === 0 || !results[0].id) {
    throw new Error(`railroad station "${name}" not found`);
  }
  return results[0];
};


const saveToFile = (data, filename = 'output/journeys.json') => {
  const dir = path.dirname(filename);
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(filename, JSON.stringify(data, null, 2), 'utf-8');
};

//  Dauer der Strecke in HH:MM
const getDurationFormatted = (journey) => {
  try {
    const departure = new Date(journey.legs[0].departure);
    const arrival = new Date(journey.legs[journey.legs.length - 1].arrival);
    const diffMs = arrival - departure;

    const totalMinutes = Math.floor(diffMs / 60000);
    const hours = Math.floor(totalMinutes / 60);
    const minutes = totalMinutes % 60;

    return `${hours}:${minutes.toString().padStart(2, '0')}`;
  } catch {
    return '?:??';
  }
};

// Differenz in Minuten
const getDelayInMinutes = (actual, planned) => {
  if (!actual || !planned) return null;
  const actualDate = new Date(actual);
  const plannedDate = new Date(planned);
  return Math.round((actualDate - plannedDate) / 60000);
};

const getDurationInMinutes = (journey) => {
  try {
    const departure = new Date(journey.legs[0].departure);
    const arrival = new Date(journey.legs[journey.legs.length - 1].arrival);
    return (arrival - departure) / 60000;
  } catch {
    return 1000000;
  }
};

// Deutsches Datums-Format
const formatTime = (isoString) => {
  if (!isoString) return '?';
  const date = new Date(isoString);
  return new Intl.DateTimeFormat('de-DE', {
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
    timeZone: 'Europe/Berlin',
  }).format(date);
};

const main = async () => {
  
  try {
    const from = await getStation(fromName);
    const to = await getStation(toName);

    // holen uns die Jorney, 10 Ergebnisse, Zwischenstationen 
    const { journeys } = await client.journeys(from, to, {
      results: 10,
      stopovers: true,
      remarks: true,
      polylines: false,
      scheduledDays: true
    });
	
    let lastArrivalTime = null;

    if (!journeys || journeys.length === 0) {
    }

    //jorney nach Dauer sortieren
    journeys.sort((a, b) => getDurationInMinutes(a) - getDurationInMinutes(b));
	  
    // jorneys nach Ankunftszeit sortieren
    // journeys.sort((a, b) => {
    //   const aArrival = new Date(a.legs[a.legs.length - 1].arrival);
    //   const bArrival = new Date(b.legs[b.legs.length - 1].arrival);
    //   return aArrival - bArrival;
    // });


    const enriched = [];

    //für jede jorney, jeden Zug, jede Haltestelle ausgeben
    journeys.forEach((journey, index) => {
      const legs = journey.legs;

      for (let i = 0; i < legs.length; i++) {
        const leg = legs[i];
        const nextLeg = legs[i + 1];

        if (!leg.stopovers) continue;

        leg.stopovers.forEach((stop) => {
          let isTransferStop = nextLeg &&
            leg.destination?.id === nextLeg.origin?.id &&
            stop.stop?.id === leg.destination?.id;
          
            let transferTimeMin = null;
	    if(isTransferStop)
	    {
	    	transferTimeMin = getDelayInMinutes(stop.departure, lastArrivalTime);
	    }

          //flache Struktur, welches einfaches einlesen ermöglicht ohne zusätzliche bearbeitung
          enriched.push({
            journey_number: index + 1,
            from: legs[0]?.origin?.name,
            to: legs[legs.length - 1]?.destination?.name,
	    planned_departure: formatTime(leg.plannedDeparture),
            departure: formatTime(leg.departure),
            delay_departure: getDelayInMinutes(leg.departure, leg.plannedDeparture),
	    planned_arrival: formatTime(leg.plannedArrival),
            arrival: formatTime(leg.arrival),
            delay_arrival: getDelayInMinutes(leg.arrival, leg.plannedArrival),
            duration: getDurationFormatted(journey),
            train: leg.line?.name,
	    train_type: leg.line?.product,
            mode: leg.mode,
            direction: leg.direction,
            stop_name: stop.stop?.name,
	    planned_stop_arrival: formatTime(stop.plannedArrival),
            stop_arrival: formatTime(stop.arrival),
	    planned_stop_departure: formatTime(stop.plannedDeparture),
            stop_departure: formatTime(stop.departure),
            delay_stop_departure: getDelayInMinutes(stop.departure, stop.plannedDeparture),
            loadFactor: leg.loadFactor || null,
          });
          lastArrivalTime = stop.arrival;		  
        });
      }
    });
    saveToFile(enriched, 'jorney/output/journeys.json');
  } catch (err) {
    process.exit(1);
  }
};

main();
