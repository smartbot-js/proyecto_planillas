# ============================================================
# Normalizar tipografía Inter en todo el proyecto
# Ejecutar desde la raíz: powershell -ExecutionPolicy Bypass -File normalizar_tipografia.ps1
# ============================================================

$TEMPLATES_DIR = "templates"
$CSS_DIR = "static/css"
$count = 0

Write-Host "============================================"
Write-Host "1. Asegurando font-family en dashboard.css"
Write-Host "============================================"

$dashboardCss = "$CSS_DIR/dashboard.css"
if (Test-Path $dashboardCss) {
    $css = Get-Content -Path $dashboardCss -Raw -Encoding UTF8
    
    # Verificar si ya tiene body con font-family
    if ($css -match "body\s*\{[^}]*font-family") {
        Write-Host "   Ya tiene body font-family, verificando..."
        # Reemplazar cualquier font-family del body por Inter
        $css = [regex]::Replace($css, 
            "(body\s*\{[^}]*?)font-family:\s*[^;]+;", 
            "`$1font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;")
        Set-Content -Path $dashboardCss -Value $css -Encoding UTF8 -NoNewline
        Write-Host "   OK Actualizado a Inter"
    } else {
        # Agregar al inicio del archivo
        $nueva_regla = "/* Tipografia global */`nbody {`n    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;`n    -webkit-font-smoothing: antialiased;`n    -moz-osx-font-smoothing: grayscale;`n}`n`n"
        $css = $nueva_regla + $css
        Set-Content -Path $dashboardCss -Value $css -Encoding UTF8 -NoNewline
        Write-Host "   OK Agregado body font-family Inter"
    }
} else {
    Write-Host "   ERROR: No se encontro $dashboardCss"
}

Write-Host ""
Write-Host "============================================"
Write-Host "2. Eliminando body font-family de templates..."
Write-Host "============================================"

$archivos = Get-ChildItem -Path $TEMPLATES_DIR -Filter "*.html" -Recurse

foreach ($archivo in $archivos) {
    $contenido = Get-Content -Path $archivo.FullName -Raw -Encoding UTF8
    $modificado = $false
    
    # Patron 1: body { ... font-family: ...; ... } (inline en <style>)
    # Quitar SOLO la linea font-family dentro de body { }
    if ($contenido -match "body\s*\{[^}]*font-family:\s*[^;]+;") {
        $contenido = [regex]::Replace($contenido, 
            "(body\s*\{[^}]*?)font-family:\s*[^;]+;\s*", 
            "`$1")
        $modificado = $true
        $count++
        Write-Host "   OK $($archivo.Name) - quitado body font-family"
    }
    
    # Patron 2: Quitar <link> duplicados de Google Fonts Inter (ya esta en base.html)
    if ($contenido -match "<link[^>]*fonts\.googleapis\.com[^>]*Inter[^>]*>") {
        # Solo quitar si NO es base.html
        if ($archivo.Name -ne "base.html") {
            $contenido = [regex]::Replace($contenido, 
                "<link[^>]*fonts\.googleapis\.com[^>]*Inter[^>]*>\s*\n?", 
                "")
            $modificado = $true
            Write-Host "   OK $($archivo.Name) - quitado link Inter duplicado"
        }
    }
    
    # Patron 3: Quitar <link preconnect fonts.googleapis> duplicados
    if ($archivo.Name -ne "base.html") {
        if ($contenido -match "<link[^>]*preconnect[^>]*fonts\.googleapis[^>]*>") {
            $contenido = [regex]::Replace($contenido, 
                "<link[^>]*preconnect[^>]*fonts\.google[^>]*>\s*\n?", 
                "")
            $modificado = $true
            Write-Host "   OK $($archivo.Name) - quitado preconnect duplicado"
        }
    }
    
    if ($modificado) {
        Set-Content -Path $archivo.FullName -Value $contenido -Encoding UTF8 -NoNewline
    }
}

Write-Host ""
Write-Host "============================================"
Write-Host "RESUMEN"
Write-Host "============================================"
Write-Host "   Templates corregidos: $count"
Write-Host "   Fuente global: Inter (en dashboard.css)"
Write-Host "   Cargada desde: base.html (Google Fonts)"
Write-Host ""
Write-Host "OK Reinicia el servidor para ver los cambios."