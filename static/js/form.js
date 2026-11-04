function cloneTemplate(templateId, idx) {
  const tpl = document.getElementById(templateId);
  const html = tpl.innerHTML.replaceAll('__IDX__', idx);
  const wrapper = document.createElement('div');
  wrapper.innerHTML = html.trim();
  return wrapper.firstElementChild;
}

function renumber(listId, countHiddenId) {
  const list = document.getElementById(listId);
  document.getElementById(countHiddenId).value = list.children.length;
}

let vueloIdx = 0;
function addVuelo() {
  const node = cloneTemplate('vuelo-template', vueloIdx++);
  document.getElementById('vuelos-list').appendChild(node);
  document.getElementById('vuelos_count').value = document.getElementById('vuelos-list').children.length;
}

let precioIdx = 0;
function addPrecio() {
  const node = cloneTemplate('precio-template', precioIdx++);
  document.getElementById('precios-list').appendChild(node);
  document.getElementById('precios_count').value = document.getElementById('precios-list').children.length;
}

let hotelMultiIdx = 0;
function addHotelMulti() {
  const node = cloneTemplate('hotel-multi-template', hotelMultiIdx++);
  document.getElementById('hoteles-list').appendChild(node);
  document.getElementById('hoteles_count').value = document.getElementById('hoteles-list').children.length;
}

let diaIdx = 0;
function addDia() {
  const node = cloneTemplate('dia-template', diaIdx++);
  document.getElementById('dias-list').appendChild(node);
  document.getElementById('dias_count').value = document.getElementById('dias-list').children.length;
}

let hotelSimpleIdx = 0;
function addHotelSimple() {
  const node = cloneTemplate('hotel-simple-template', hotelSimpleIdx++);
  document.getElementById('hoteles-simple-list').appendChild(node);
  document.getElementById('hoteles_simple_count').value = document.getElementById('hoteles-simple-list').children.length;
}

let hotelPrecioIdx = 0;
function addHotelPrecioItin() {
  const node = cloneTemplate('hotel-precio-template', hotelPrecioIdx++);
  document.getElementById('hoteles-precio-list').appendChild(node);
  document.getElementById('hoteles_precio_count').value = document.getElementById('hoteles-precio-list').children.length;
}

function removeAndCount(el, listId, countId) {
  el.closest('.repeat-block').remove();
  document.getElementById(countId).value = document.getElementById(listId).children.length;
}

function toggleHotelesModo() {
  const modo = document.querySelector('input[name="hoteles_modo"]:checked').value;
  document.getElementById('hoteles-modo-simple').style.display = modo === 'simple' ? 'block' : 'none';
  document.getElementById('hoteles-modo-precio').style.display = modo === 'precio' ? 'block' : 'none';
}

function togglePrecioItin() {
  document.getElementById('precio-itin-container').style.display = document.getElementById('hay_precio').checked ? 'block' : 'none';
}
