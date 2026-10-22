const colors = [
"linear-gradient(135deg,#667eea,#764ba2)",
"linear-gradient(135deg,#ff9a9e,#fad0c4)",
"linear-gradient(135deg,#a18cd1,#fbc2eb)",
"linear-gradient(135deg,#43cea2,#185a9d)"
];

let index = 0;

setInterval(function(){

document.body.style.background = colors[index];

index++;

if(index >= colors.length){
index = 0;
}

}, 6000);