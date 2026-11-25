var xhr_qqid = new XMLHttpRequest();

xhr_qqid.open("GET", "/api/top_qqid");


xhr_qqid.onreadystatechange = function () {

    if (xhr_qqid.readyState === 4 && xhr_qqid.status === 200) {


        var data = JSON.parse(xhr_qqid.response);


        console.log(data);
        
        const top1_qqid=document.getElementById("top1_qqid");
        const top2_qqid=document.getElementById("top2_qqid");
        const top3_qqid=document.getElementById("top3_qqid");

        document.body.setAttribute("top1_qqid", data.top1_qqid);
        document.body.setAttribute("top2_qqid", data.top2_qqid);
        document.body.setAttribute("top3_qqid", data.top3_qqid);
        
        console.log(document.body.getAttribute("top1_qqid"));
        console.log(document.body.getAttribute("top2_qqid"));
        console.log(document.body.getAttribute("top3_qqid"));
        top1_qqid.textContent=document.body.getAttribute("top1_qqid");
        top2_qqid.textContent=document.body.getAttribute("top2_qqid");
        top3_qqid.textContent=document.body.getAttribute("top3_qqid");
        // document.getElementById("top1_qqid").textContent = document.body.getAttribute("top1_qqid");
        // documenr.getElementById("top2_qqid").textContent = document.body.getAttribute("top2_qqid");
        // documenr.getElementById("top3_qqid").textContent = document.body.getAttribute("top3_qqid");
        var top1_img_url = `https://q.qlogo.cn/headimg_dl?dst_uin=${data.top1_qqid}&spec=640&img_type=jpg`;
        var top2_img_url = `https://q.qlogo.cn/headimg_dl?dst_uin=${data.top2_qqid}&spec=640&img_type=jpg`;
        var top3_img_url = `https://q.qlogo.cn/headimg_dl?dst_uin=${data.top3_qqid}&spec=640&img_type=jpg`;
        let top1_img = document.getElementById("top1_img");
        let top2_img = document.getElementById("top2_img");
        let top3_img = document.getElementById("top3_img");

        let img_1 = document.createElement('img');
        img_1.src = top1_img_url;
        img_1.alt = "top1";
        img_1.className="div_pp";

        top1_img.appendChild(img_1);
        


        let img_2 = document.createElement('img');
        img_2.src = top2_img_url;
        img_2.alt = "top2";
        img_2.className = "div_pp";
        top2_img.appendChild(img_2);

        let img_3 = document.createElement('img');
        img_3.src = top3_img_url;
        img_3.alf = "top3";
        img_3.className="div_pp";
        top3_img.appendChild(img_3);




        


        

        // document.body.setAttribute("top1_img_url" ,top1_img_url)
        // document.body.setAttribute("top2_img_url" ,top2_img_url)
        // document.body.setAttribute("top3_img_url" ,top3_img_url)


        

        
    }



};


xhr_qqid.send();