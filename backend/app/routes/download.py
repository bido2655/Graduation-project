"""
Download Routes - Endpoints for downloading diagrams as PNG.
"""
import time
import requests
from fastapi import APIRouter, HTTPException, Response

from ..models import DownloadRequest
from ..services import decode_plantuml, create_diagram_image

router = APIRouter()


@router.get("/download-png/{encoded_plantuml}")
async def download_png(encoded_plantuml: str):
    """
    Download diagram as PNG file directly.
    Example: GET /download-png/~hABCD123...
    """
    try:
        # Decode the PlantUML code
        plantuml_code = decode_plantuml(encoded_plantuml)
        
        # Use Kroki.io for reliable PNG generation
        response = requests.post(
            'https://kroki.io/plantuml/png',
            json={
                "diagram_source": plantuml_code,
                "diagram_type": "plantuml"
            },
            timeout=30
        )
        
        if response.status_code == 200 and len(response.content) > 100:
            # Generate filename
            timestamp = int(time.time())
            filename = f"nexus-diagram-{timestamp}.png"
            
            return Response(
                content=response.content,
                media_type="image/png",
                headers={
                    "Content-Disposition": f"attachment; filename=\"{filename}\"",
                    "Access-Control-Expose-Headers": "Content-Disposition"
                }
            )
        else:
            # Fallback to creating an image
            img_bytes = create_diagram_image(plantuml_code)
            if img_bytes:
                return Response(
                    content=img_bytes,
                    media_type="image/png",
                    headers={
                        "Content-Disposition": f"attachment; filename=\"diagram-fallback.png\"",
                        "Access-Control-Expose-Headers": "Content-Disposition"
                    }
                )
            raise HTTPException(status_code=500, detail="Failed to generate PNG")
            
    except Exception as e:
        print(f"Download PNG error: {e}")
        raise HTTPException(status_code=500, detail=f"Error generating PNG: {str(e)}")


@router.post("/download-png-from-source")
async def download_png_from_source(request: DownloadRequest):
    """
    Download PNG from raw PlantUML source code.
    """
    try:
        if not request.diagram_source or not request.diagram_source.strip():
            raise HTTPException(status_code=400, detail="PlantUML source code is required")
        
        # Use Kroki.io for PNG generation
        response = requests.post(
            'https://kroki.io/plantuml/png',
            json={
                "diagram_source": request.diagram_source,
                "diagram_type": "plantuml"
            },
            timeout=30
        )
        
        if response.status_code == 200 and len(response.content) > 100:
            timestamp = int(time.time())
            filename = f"nexus-diagram-{timestamp}.png"
            
            return Response(
                content=response.content,
                media_type="image/png",
                headers={
                    "Content-Disposition": f"attachment; filename=\"{filename}\"",
                    "Access-Control-Expose-Headers": "Content-Disposition"
                }
            )
        else:
            # Create fallback image
            img_bytes = create_diagram_image(request.diagram_source)
            if img_bytes:
                return Response(
                    content=img_bytes,
                    media_type="image/png",
                    headers={
                        "Content-Disposition": f"attachment; filename=\"diagram-fallback.png\"",
                        "Access-Control-Expose-Headers": "Content-Disposition"
                    }
                )
            raise HTTPException(status_code=500, detail="Failed to generate PNG")
            
    except Exception as e:
        print(f"Download from source error: {e}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")
