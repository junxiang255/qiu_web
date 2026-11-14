//播放按钮
let playBut = document.getElementById("play");
//播放器
let myAudio = document.getElementById("myAudio");
//控件
let controlDom = document.getElementById('control');

playBut.addEventListener("click", playF);
//点击事件
function playF() {
    //判断当前是否在播放
    let flag = Array.from(controlDom.classList).some(function (item) {
    return item == "active";
    });
    if (flag) {
    //播放中点击暂停
    controlDom.classList.remove('active');
    myAudio.pause();
    } else {
    controlDom.classList.add('active');
    myAudio.play();
    }
}

// 获取时间和歌词
function getLrcObj(str) {
    const arr = str.split(']');
    return {
    time: formateTime(arr[0].substring(1)),
    word: arr[1],
    };
}
// 把时间转化成秒
function formateTime(str) {
    const arr = str.split(':');
    return +arr[0] * 60 + +arr[1];
}

function getLrc(str) {
    const strArr = str.split('\n');
    let arr = [];
    for (let i = 0; i < strArr.length; i++) {
    let obj = getLrcObj(strArr[i]);
    arr.push(obj);
    }
    return arr;
}

//显示歌词
let lrcArr = [];
function showLrc() {
    const fragment = document.createDocumentFragment();
    lrcArr = getLrc(lrc);
    for (let i = 0; i < lrcArr.length; i++) {
    li = document.createElement('li');
    li.textContent = lrcArr[i].word;//歌词
    fragment.appendChild(li);
    }
    document.querySelector('.lrc-box').appendChild(fragment);
}

showLrc();


// 获取当前播放的歌词下标
function getArrIndex() {
    const currentTime = myAudio.currentTime;
    let index = lrcArr.findIndex(function (item) {
    return item.time > currentTime
    })
    if (index == -1) {
    return lrcArr.length - 1;
    }
    return index - 1;
}

//滚动区域高度
let ulDom = document.querySelector(".container ul");
const containerH = document.querySelector(".container").clientHeight;
//最大移动高度
const maxOffset = ulDom.clientHeight - containerH;
//实时获取歌曲播放进度
function setLrc() {
    setProgress();//设置进度条
    const nowIndex = getArrIndex();
    const allLiHeight = nowIndex * 30;
    const half = containerH / 2; // 容器的一半高度
    // 移动多少
    let offset = allLiHeight + 30 / 2 - half;
    if (offset < 0) {
    offset = 0;
    }
    if (offset > maxOffset) {
    offset = maxOffset;
    }

    //滚动歌词
    ulDom.style.transform = `translateY(-${offset}px)`;

    let li = document.querySelector('.on');
    if (li) {
    li.classList.remove('on');
    }
    //设置 当前歌词高亮
    li = ulDom.children[nowIndex];

    if (li) {
    li.classList.add('on');
    }
}
// 监听播放进度
myAudio.addEventListener('timeupdate', setLrc);


// 设置进度条
const slider = document.getElementById('myRange');
const progress = document.getElementById('progress');

//进度提拖动
slider.oninput = function () {
    progress.style.width = `${this.value}%`;
    // 获取音乐总时长，单位是秒
    let duration = myAudio.duration;
    //修改当前播放时间
    myAudio.currentTime = this.value / 100 * duration;
}

//设置进度条
function setProgress() {
    let duration = myAudio.duration;
    const currentTime = myAudio.currentTime;
    let val = parseInt(currentTime / duration * 100);
    //设置进度提值 
    slider.value = val;
    progress.style.width = `${val}%`;
}
