// Получаем элементы
const menuToggle = document.getElementById('menuToggle');
const sidebar = document.getElementById('menuSelect');
const overlay = document.getElementById('overlay');
const toggle_block = document.getElementById('toggle_block');
const block_application = document.getElementById('block_application');

function toggleMenu() {
  sidebar.classList.toggle('open');
  overlay.classList.toggle('on');
}
menuToggle.addEventListener('click', toggleMenu);
overlay.addEventListener('click', toggleMenu);

function toggleApplicationBlock() {
  block_application.classList.toggle('toggled');

  if (block_application.classList.contains('toggled')) {
    block_application.style.maxHeight = '40px';
  } else {
    block_application.style.maxHeight = block_application.scrollHeight + 'px';
  }
}

toggle_block.addEventListener('click', toggleApplicationBlock);
