eel.expose(init_matrix);
function init_matrix(width, height, pitch, diameter) {
    const matrix_container = document.createElement('div');
    matrix_container.classList.add('matrix-container');
    matrix_container.style.gridTemplateColumns = `repeat(${width}, ${diameter}px)`;
    matrix_container.style.gridTemplateRows = `repeat(${height}, ${diameter}px)`;

    matrix_container.style.gap = `${pitch - diameter}px`;
    matrix_container.style.padding = `${pitch - diameter}px`;

    const num_pixels = width * height;
    for (let i = 0; i < num_pixels; i++) {
        const pixel = document.createElement('div');
        pixel.classList.add('pixel');
        matrix_container.appendChild(pixel);
    }

    document.querySelector('main').appendChild(matrix_container);
}

eel.expose(set_pixels);
function set_pixels(data) {
    console.log(data);
    const pixels = document.querySelectorAll('.pixel');
    for (let i = 0; i < pixels.length; i++) {
        const color = `rgb(${data[i][0]}, ${data[i][1]}, ${data[i][2]})`
        pixels[i].style.backgroundColor = color;
    }
}