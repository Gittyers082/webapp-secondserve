/** DOM helpers shared by the live Partner tables. User content is inserted as text, never HTML. */
import type { FoodArt } from '../data/types';

export function td(className = '', text = ''): HTMLTableCellElement {
  const cell = document.createElement('td');
  if (className) cell.className = className;
  if (text) cell.textContent = text;
  return cell;
}

export function badge(label: string, tone: string): HTMLElement {
  const element = document.createElement('span');
  element.className = `pill ${tone}`;
  element.textContent = label;
  return element;
}

export function foodCell(name: string, art: FoodArt): HTMLTableCellElement {
  const cell = td('name');
  const wrap = document.createElement('span');
  wrap.className = 'food-cell';
  const thumb = document.createElement('span');
  thumb.className = 'food-thumb';
  const img = document.createElement('img');
  img.src = `/photos/480/${art}.jpg`;
  img.alt = '';
  img.loading = 'lazy';
  img.decoding = 'async';
  img.style.width = '100%';
  img.style.height = '100%';
  img.style.objectFit = 'cover';
  thumb.append(img);
  wrap.append(thumb, document.createTextNode(name));
  cell.append(wrap);
  return cell;
}
