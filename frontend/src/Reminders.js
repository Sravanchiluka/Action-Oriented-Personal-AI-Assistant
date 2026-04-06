import React, {useEffect, useState} from "react";
import axios from "axios";

function Reminders(){

    const [reminders,setReminders] = useState("");

    const loadReminders = async () => {

        const res = await axios.get("http://127.0.0.1:8000/reminders");

        setReminders(res.data.reminders);
    }

    useEffect(()=>{
        loadReminders();
    },[]);

    return(

        <div style={{padding:20}}>

            <h2>Reminders</h2>

            <pre>{reminders}</pre>

        </div>

    )
}

export default Reminders;