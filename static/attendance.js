function confirmAttendance() {
    return confirm("Are you sure you want to mark attendance?");
}

function deleteAttendance(attendanceId) {
    attendanceId = parseInt(attendanceId); // convert string to int
    if(confirm("Are you sure you want to delete this record?")) {
        fetch(`/delete_attendance/${attendanceId}`, {
            method: 'DELETE'
        })
        .then(res => res.json())
        .then(data => {
            if(data.success) {
                // Remove row from table
                const row = document.getElementById(`row-${attendanceId}`);
                if(row) row.remove();
            } else {
                alert("Error deleting record");
            }
        })
        .catch(err => {
            console.log("Fetch error:", err);
            alert("Error deleting record");
        });
    }
}
