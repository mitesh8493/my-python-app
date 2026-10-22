function logout(){

alert("Logout Successful");

window.location.href="/";

}
function logout(){

alert("Logout Successful");

window.location.href="/";

}
function logout() {
    if(confirm("Are you sure you want to logout?")) {
        window.location.href = "/logout";  // Flask logout route
    }
}
// Example: filter projects by name
function filterProjects() {
    let input = document.getElementById('searchInput').value.toLowerCase();
    let rows = document.querySelectorAll('.dashboard table tr');
    rows.forEach((row, index) => {
        if(index === 0) return; // skip header
        let projectName = row.cells[1].innerText.toLowerCase();
        row.style.display = projectName.includes(input) ? '' : 'none';
    });
}
