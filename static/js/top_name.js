var xhr_name = new XMLHttpRequest();

xhr_name.open("GET", "/api/top_name");


xhr_name.onreadystatechange = function () {

    if (xhr_name.readyState === 4 && xhr_name.status === 200) {


        var data = JSON.parse(xhr_name.response);


        console.log(data);
        
        const top1_name=document.getElementById("top1_name");
        const top2_name=document.getElementById("top2_name");
        const top3_name=document.getElementById("top3_name");

        document.body.setAttribute("top1_name", data.top1_name);
        document.body.setAttribute("top2_name", data.top2_name);
        document.body.setAttribute("top3_name", data.top3_name);
        
        console.log(document.body.getAttribute("top1_name"));
        console.log(document.body.getAttribute("top2_name"));
        console.log(document.body.getAttribute("top3_name"));
        top1_name.textContent=document.body.getAttribute("top1_name");
        top2_name.textContent=document.body.getAttribute("top2_name");
        top3_name.textContent=document.body.getAttribute("top3_name");
        // document.getElementById("top1_name").textContent = document.body.getAttribute("top1_name");
        // documenr.getElementById("top2_name").textContent = document.body.getAttribute("top2_name");
        // documenr.getElementById("top3_name").textContent = document.body.getAttribute("top3_name");


    }



};


xhr_name.send();