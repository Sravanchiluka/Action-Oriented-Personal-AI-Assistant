import React,{useEffect,useState} from "react";
import axios from "axios";

function Calendar(){

 const [events,setEvents] = useState("");

 const loadEvents = async () => {

  const res = await axios.get("http://127.0.0.1:8000/calendar");

  setEvents(res.data.events);

 };

 useEffect(()=>{
  loadEvents();
 },[]);

 return(

  <div style={{padding:20}}>

   <h2>Event Scheduler</h2>

   <pre>{events}</pre>

  </div>

 );

}

export default Calendar;
