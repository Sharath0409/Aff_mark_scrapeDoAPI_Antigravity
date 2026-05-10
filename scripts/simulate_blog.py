from core.content_generator import ContentGenerator
import json

def simulate():
    # Mock data to simulate what the scraper would find
    mock_products = [
        {
            "title": "Logitech G502 HERO High Performance Wired Gaming Mouse",
            "price": "$39.99",
            "rating": "4.7",
            "review_count": "55,000",
            "features": "25K Sensor, 11 Programmable Buttons, Adjustable Weights, RGB",
            "url": "https://www.amazon.com/Logitech-G502-Performance-Gaming-Mouse/dp/B07GBZ4Q68"
        },
        {
            "title": "Razer DeathAdder V2 Gaming Mouse",
            "price": "$44.99",
            "rating": "4.6",
            "review_count": "28,000",
            "features": "20K DPI Optical Sensor, 8 Programmable Buttons, Chroma RGB",
            "url": "https://www.amazon.com/Razer-DeathAdder-V2-Gaming-Mouse/dp/B082G5NJ5C"
        }
    ]

    generator = ContentGenerator()
    topic = "The Best Gaming Mice for Competitive Play"
    keyword = "gaming mouse"
    
    # Generate the post using the new logic
    print("🎨 Generating simulation with new visual style...")
    html_output = generator.generate_full_post(topic, keyword, mock_products)
    
    with open("simulation_preview.html", "w", encoding="utf-8") as f:
        f.write(html_output)
    
    print("✅ Simulation complete! Saved to simulation_preview.html")

if __name__ == "__main__":
    simulate()
