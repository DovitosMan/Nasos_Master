// Получаем элементы
const menuToggle = document.getElementById('menuToggle');
const sidebar = document.getElementById('menuSelect');
const overlay = document.getElementById('overlay');
const toggle_block = document.getElementById('toggle_block');
const block_application = document.getElementById('block_application');

menuToggle.addEventListener('click', () => {
    // Переключаем классы для меню и контента
    sidebar.classList.toggle('open');
    overlay.classList.toggle('on');
});
toggle_block.addEventListener('click', () => {
    //Сворачивание блока приложения
    block_application.classList.toggle('toggled');
});
if (toggle_block.classList.contains('toggled')) {
  toggle_block.style.maxHeight = '20px';
} else {
  toggle_block.style.maxHeight = toggle_block.scrollHeight + 'px';
}



