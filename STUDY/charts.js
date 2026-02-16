/* =========================================
   CHARTS LAYER: Visualizations
   ========================================= */

const charts = {
    updateCircularProgress: function(percentage) {
        const circle = document.getElementById('progressCircle');
        const text = document.getElementById('progressText');
        const val = document.getElementById('progressVal');

        if(!circle) return;

        // Update Text
        text.innerText = `${percentage}%`;
        val.innerText = `${percentage}%`;

        // Update CSS Conic Gradient
        // #4f46e5 is the purple color, #f3f4f6 is grey background
        circle.style.background = `conic-gradient(
            #4f46e5 ${percentage * 3.6}deg, 
            #f3f4f6 ${percentage * 3.6}deg
        )`;
    }
};