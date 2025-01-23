// Получаем элементы
const menuToggle = document.getElementById('menuToggle');
const sidebar = document.getElementById('menuSelect');
const overlay = document.getElementById('overlay');



// Задаем такой же сдвиг content как и у sidebar
// if (contentShift) {
//     contentShift.style.marginLeft = getComputedStyle(sidebar).left;
// }
// Добавляем обработчик события на кнопку
menuToggle.addEventListener('click', () => {
    // Переключаем классы для меню и контента
    sidebar.classList.toggle('open');
    overlay.classList.toggle('on');
});




