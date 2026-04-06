import React, {useEffect, useState} from "react";
import axios from "axios";

function Notes(){

    const [notes,setNotes] = useState("");

    const loadNotes = async () => {

        const res = await axios.get("http://127.0.0.1:8000/notes");

        setNotes(res.data.notes);
    }

    useEffect(()=>{
        loadNotes();
    },[]);

    return(

        <div style={{padding:20}}>

            <h2>Notes</h2>

            <pre>{notes}</pre>

        </div>

    )
}

export default Notes;