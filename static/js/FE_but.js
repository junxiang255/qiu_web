function setActivePage(page) {
    // 1. 切换主内容区域
    document.getElementById('FE_1').style.display = 'none';
    document.getElementById('FE_2').style.display = 'none';
    document.getElementById('FE_3').style.display = 'none';
    document.getElementById('FE_4').style.display = 'none';
    document.getElementById('FE_' + page).style.display = 'block';
   
    for (let i = 1; i <= 4; i++) {
        // 处理普通按钮（不带 _active）
        const normal = document.getElementById('page-item_' + i);
        if (normal) {
            normal.style.display = (i === page) ? 'none' : 'block';
        }
        // 处理激活按钮（带 _active）
        const active = document.getElementById('page-item_' + i + '_active');
        if (active) {
            active.style.display = (i === page) ? 'block' : 'none';
        }
    }
}

