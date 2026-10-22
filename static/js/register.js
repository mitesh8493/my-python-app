function validateForm(){

let password=document.getElementById("password").value;

if(password.length < 6){
alert("Password must be at least 6 characters");
return false;
}

alert("Registration Successful");

return true;

}
