#!/usr/bin/env python3
"""
Service Manager - Run Both Bot and MTProto Scraper
Manages both the Telegram bot and MTProto scraper services
"""

import asyncio
import subprocess
import sys
import signal
import logging
import time

logger = logging.getLogger(__name__)

class ServiceManager:
    """Manages both bot and scraper services"""
    
    def __init__(self):
        self.bot_process = None
        self.scraper_process = None
        self.running = False
    
    async def start_services(self):
        """Start both services"""
        print("🚀 Starting Ultra-Fast Trading System...")
        print("=" * 50)
        
        self.running = True
        
        try:
            # Start Telegram Bot (for user interface)
            print("📱 Starting Telegram Bot interface...")
            self.bot_process = subprocess.Popen([
                sys.executable, "bot.py"
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            # Wait a moment for bot to initialize
            await asyncio.sleep(3)
            
            # Start MTProto Scraper (for ultra-fast monitoring)
            print("🔥 Starting MTProto Scraper...")
            self.scraper_process = subprocess.Popen([
                sys.executable, "mtproto_scraper.py"
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            print("✅ Both services started successfully!")
            print("\n🎯 System Status:")
            print("📱 Telegram Bot: Running (user interface)")
            print("🔥 MTProto Scraper: Running (ultra-fast monitoring)")
            print("\n⚡ Ready for 275ms trade execution!")
            
            # Monitor services
            await self._monitor_services()
            
        except Exception as e:
            print(f"❌ Failed to start services: {e}")
            await self.stop_services()
    
    async def _monitor_services(self):
        """Monitor both services and restart if needed"""
        while self.running:
            try:
                # Check bot process
                if self.bot_process and self.bot_process.poll() is not None:
                    print("⚠️ Telegram bot stopped, restarting...")
                    self.bot_process = subprocess.Popen([
                        sys.executable, "bot.py"
                    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                
                # Check scraper process
                if self.scraper_process and self.scraper_process.poll() is not None:
                    print("⚠️ MTProto scraper stopped, restarting...")
                    self.scraper_process = subprocess.Popen([
                        sys.executable, "mtproto_scraper.py"
                    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                
                await asyncio.sleep(5)  # Check every 5 seconds
                
            except Exception as e:
                logger.error(f"Error monitoring services: {e}")
                await asyncio.sleep(10)
    
    async def stop_services(self):
        """Stop both services"""
        print("\n🔄 Stopping services...")
        self.running = False
        
        if self.scraper_process:
            print("🔥 Stopping MTProto scraper...")
            self.scraper_process.terminate()
            try:
                self.scraper_process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.scraper_process.kill()
        
        if self.bot_process:
            print("📱 Stopping Telegram bot...")
            self.bot_process.terminate()
            try:
                self.bot_process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.bot_process.kill()
        
        print("✅ All services stopped")

# Global service manager
service_manager = ServiceManager()

def signal_handler(signum, frame):
    """Handle shutdown signals"""
    print(f"\n📝 Received signal {signum}")
    asyncio.create_task(service_manager.stop_services())

async def main():
    """Main entry point"""
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        await service_manager.start_services()
    except KeyboardInterrupt:
        print("\n👋 Shutdown requested by user")
    except Exception as e:
        print(f"❌ Fatal error: {e}")
    finally:
        await service_manager.stop_services()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 System stopped by user")
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        sys.exit(1)