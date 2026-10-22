function logoutConfirm(){

let confirmLogout = confirm("Are you sure you want to logout?");

if(confirmLogout){

window.location.href="/";

}

}
console.log("Admin Dashboard Loaded");

let cards = document.querySelectorAll(".card");

cards.forEach(function(card){

card.addEventListener("click", function(){

alert("Feature coming soon!");

});


});
function filterFeedback() {
    let input = document.getElementById("feedbackSearch").value.toLowerCase();
    let rows = document.querySelectorAll(".feedback-table tr");
    rows.forEach((row, index) => {
        if(index === 0) return; // skip header
        let cells = row.getElementsByTagName("td");
        let match = false;
        for(let i=1; i<cells.length; i++){ // skip ID column
            if(cells[i].innerText.toLowerCase().includes(input)){
                match = true;
                break;
            }
        }
        row.style.display = match ? "" : "none";
    });
}
