dragElement(document.getElementById("drag_player"));
dragElement(document.getElementById("drag_container"));
function dragElement(elmnt) {
  var pos1 = 0, pos2 = 0, pos3 = 0, pos4 = 0;
  if (document.getElementById(elmnt.id + "header")) {
    // 如果存在，则标题是移动 DIV 的起点
    document.getElementById(elmnt.id + "header").onmousedown = dragMouseDown;
  } else {
    // 否则，从 DIV 内部的任何位置移动 DIV
    elmnt.onmousedown = dragMouseDown;
  }

  function dragMouseDown(e) {
    e = e || window.event;
    e.preventDefault();
    // 获取开始时的鼠标光标位置
    pos3 = e.clientX;
    pos4 = e.clientY;
    document.onmouseup = closeDragElement;
    // 每当光标移动时调用一个函数
    document.onmousemove = elementDrag;
  }

  function elementDrag(e) {
    e = e || window.event;
    e.preventDefault();
    // 计算新的光标位置
    pos1 = pos3 - e.clientX;
    pos2 = pos4 - e.clientY;
    pos3 = e.clientX;
    pos4 = e.clientY;
    // 设置元素的​​新位置
    elmnt.style.top = (elmnt.offsetTop - pos2) + "px";
    elmnt.style.left = (elmnt.offsetLeft - pos1) + "px";
  }

  function closeDragElement() {
    // 鼠标按钮释放时停止移动
    document.onmouseup = null;
    document.onmousemove = null;
  }
}