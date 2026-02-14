/**
 * Export Module - Save/Load .trv files, PDF export
 */

const ExportModule = (function() {
    
    // Initialize export controls
    function init() {
        document.getElementById('btn-save').addEventListener('click', saveProject);
        document.getElementById('btn-load').addEventListener('click', loadProject);
        document.getElementById('btn-export-pdf').addEventListener('click', exportPDF);
        
        // Setup file input handler
        document.getElementById('file-input').addEventListener('change', handleFileSelect);
    }
    
    // Save project to browser download
    function saveProject() {
        const projectData = UIModule.getProjectState();
        const json = JSON.stringify(projectData, null, 2);
        
        // Create blob and download
        const blob = new Blob([json], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        
        const a = document.createElement('a');
        a.href = url;
        a.download = `route_project_${Date.now()}.trv`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }
    
    // Trigger file selection for loading
    function loadProject() {
        document.getElementById('file-input').click();
    }
    
    // Handle file selection
    function handleFileSelect(event) {
        const file = event.target.files[0];
        if (!file) return;
        
        if (!file.name.endsWith('.trv')) {
            alert('Please select a .trv file');
            return;
        }
        
        const reader = new FileReader();
        reader.onload = function(e) {
            try {
                const projectData = JSON.parse(e.target.result);
                UIModule.loadProjectState(projectData);
                alert('Project loaded successfully!');
            } catch (error) {
                console.error('Error loading project:', error);
                alert('Failed to load project file');
            }
        };
        reader.readAsText(file);
        
        // Reset input so same file can be loaded again
        event.target.value = '';
    }
    
    // Export to PDF
    async function exportPDF() {
        const projectData = UIModule.getProjectState();
        
        if (Object.keys(projectData.stations).length === 0) {
            alert('Please add at least one station before exporting');
            return;
        }
        
        // Show loading
        document.getElementById('loading').style.display = 'flex';
        document.querySelector('.loading-overlay p').textContent = 'Generating PDF...';
        
        try {
            const response = await fetch('/api/export/pdf', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(projectData)
            });
            
            if (!response.ok) {
                throw new Error('PDF generation failed');
            }
            
            // Download the PDF
            const blob = await response.blob();
            const url = URL.createObjectURL(blob);
            
            const a = document.createElement('a');
            a.href = url;
            a.download = `route_map_${Date.now()}.pdf`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
            
            alert('PDF exported successfully!');
            
        } catch (error) {
            console.error('Error exporting PDF:', error);
            alert('Failed to export PDF');
        } finally {
            document.getElementById('loading').style.display = 'none';
            document.querySelector('.loading-overlay p').textContent = 'Querying railway data...';
        }
    }
    
    // Public API
    return {
        init,
        saveProject,
        loadProject,
        exportPDF
    };
})();

// Initialize export module on load
document.addEventListener('DOMContentLoaded', function() {
    ExportModule.init();
});
