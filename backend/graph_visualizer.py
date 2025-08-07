from agent import agentic_workflow
from IPython.display import Image, display

def visualize_graph():
    """
    Generates a PNG image of the compiled LangGraph workflow.
    """
    try:
        # Get the graph object
        graph = agentic_workflow.get_graph()
        
        # Draw the graph and get the PNG bytes
        png_bytes = graph.draw_mermaid_png()
        
        # Save the image to a file
        with open("agri_sarthi_workflow.png", "wb") as f:
            f.write(png_bytes)
            
        print("Successfully generated 'agri_sarthi_workflow.png'")
        
        # If in a Jupyter environment, display the image
        try:
            display(Image(png_bytes))
        except NameError:
            # Not in a Jupyter environment, just print success message
            pass
            
    except Exception as e:
        print(f"Error generating graph visualization: {e}")
        print("Please ensure you have 'playwright' and its browser dependencies installed.")
        print("Run: `pip install playwright` and `playwright install`")

if __name__ == "__main__":
    visualize_graph()
