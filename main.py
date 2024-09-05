import machine
import utime
import socket
import network
import adafruit_sgp30
import bme280
import uasyncio
import _thread
import os


#Global Variables
ssid = 'Gareth\'s Galaxy A52s 5G'       #WLAN Name
password = '        '                   #WLAN Password
co2eq = 0                               #Carbon Dioxide Equivalent
tvoc = 0                                #Total Volatile Organic Compounds
climate_values = ['N/A', 'N/A', 'N/A']  #Default values for temperature, humidity & air pressure.
Beeping = False                         #Records if the buzzer is currently beeping.
BeepingOverride = False                 #Records whether the beeping override button has been pressed. 

#Button Pins
ButtonOverrideBeeping = machine.Pin(0, machine.Pin.IN, machine.Pin.PULL_DOWN)
ButtonChangeDisplay = machine.Pin(1, machine.Pin.IN, machine.Pin.PULL_DOWN)

#Climate Sensor Pins
sdaPINClimate=machine.Pin(4)
sclPINClimate=machine.Pin(5)

#Air Quality Sensor Pins
sdaPINQuality=machine.Pin(6)
sclPINQuality=machine.Pin(7)

#Control of lights in the display
Green = machine.Pin(10, machine.Pin.OUT)
Yellow = machine.Pin(11, machine.Pin.OUT)
Red = machine.Pin(12, machine.Pin.OUT)

#Initialize Buzzer
Buzzer = machine.PWM(machine.Pin(15))
Buzzer.duty_u16(0) 
Frequency = 1000
Buzzer.freq(Frequency)

#Initialize Climate Sensor - BME280
i2c = machine.I2C(0,sda=sdaPINClimate, scl=sclPINClimate, freq=400000)
bme = bme280.BME280(i2c=i2c) 

#Initialize Air Quality Scenser - SGP30
i2c_1 = machine.I2C(1,sda=sdaPINQuality, scl=sclPINQuality, freq=400000)
sgp = adafruit_sgp30.Adafruit_SGP30(i2c_1)


###################################Sensors#################################################

async def ObtainSensorReadings():
    while True:
        ObtainClimateReadings()
        ObtainAirQualityReadings()
        CheckSensorReadings()
        await uasyncio.sleep(5)
    
#Methods which obtain the readings from the sensors. 
def ObtainClimateReadings():
    global bme
    global climate_values
    try:
        bme = bme280.BME280(i2c=i2c)
        print(bme.values)
        climate_values = [bme.values[0],bme.values[1],bme.values[2]]
    except Exception as e:
        print("Exception occurred obtaining climate readings: " +str(e))
        pass


def ObtainAirQualityReadings():
    global co2eq
    global tvoc
    try:
            co2eq, tvoc = sgp.iaq_measure()
            if co2eq == 400:
                print("Initializing air quality sensor")
            else:
                print("CO2 concentration = %s ppm \t TVOC = %s ppb" % (co2eq, tvoc))
    except OSError as e:
        print("Exception occurred obtaining air quality reading: " + str(e))
        pass 

###################################Web Server#################################################

#HTML for webserver
def Webpage():
    global co2eq
    global tvoc
    
    co2eq = "N/A" if co2eq == 0 else co2eq
    tvoc = "N/A" if tvoc == 0 else tvoc
    
    html = f"""
            <!DOCTYPE html>
            <html>
            <head>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
            body {{
                font-family: Arial, sans-serif;
                margin: 0;
                padding: 0;
                background-color: #f4f4f4;
                }}
                    
            table {{
                border-collapse: collapse;
                width: 90%;
                margin-left: 5%;
                margin-right: 5%;
                box-shadow: 0 0 10px rgba(0, 0, 0, 0.1);
                }}

            th, td {{
                border: 1px solid #dddddd;
                text-align: left;
                padding: 12px;
                width: 50%; 
                }}
              
            th:first-child{{
                text-align:left;
                }}
              
            th{{
                background-color:#dddddd;
                text-align: center;
                }}
              
            td {{
                text-align: left;
                }}
                        
            td:nth-child(2) {{
                text-align: center;
                }}
                        
            tr:nth-child(odd){{
                background-color: white;
                }}
             
            tr:nth-child(even) {{
                background-color: #f0f8ff; /* Light blue for even rows */
                }}                      
         
            h1 {{
                background-color: #00008b; /* Dark blue background for header */
                color: #fff; /* White text color */
                padding: 20px; /* Add padding for spacing */
                text-align: center; /* Center align text */
                margin top: 0px;
                }}
                        
            p {{
                margin-top: 20px;
                margin-left: 5%;
                margin-right:5%;
                }}
                
            @media only screen and (max-width: 600px) {{
                table {{
                    width: 90%;
                    margin: auto;
                }}

                th, td {{
                    padding: 6px;
                }}
            }}
            </style>
            </head>
            <body>
            <h1>Climate and Air Quality Readings</h1>
            <table>
            <tr>
            <th>Parameters</th>
            <th>Value</th>
            </tr>
            <tr>
            <td>Temperature</td>
            <td>{climate_values[0]}</td></tr>
            <tr>
            <td>Air Pressure</td>
            <td>{climate_values[1]}</td>
            </tr>
            <tr>
            <td>Humidity</td>
            <td>{climate_values[2]}</td>
            </tr>
            <tr>
            <td>Carbon Dioxide</td>
            <td>{co2eq} ppm</td>
            </tr>
            <tr>
            <td>Total Volatile Organic Compounds</td>
            <td>{tvoc} ppb</td>
            </tr>
            </table>
            <p>Source: BME280 sensor for temperature, humidity and air pressure. SDP30 sensor for Carbon Dioxide and Total Volatile Organic Compounds.</p>         
            </body>
            </html>
            """
    return str(html)


#Methods which connect to WLAN, Open Socket and Serve HTML.
def Connect():
    max_retries = 2
    retry_count = 0

    while retry_count < max_retries:
        # Connect to WLAN
        wlan = network.WLAN(network.STA_IF)
        wlan.active(True)
        
        try:
            wlan.connect(ssid, password)
            while not wlan.isconnected():
                print('Waiting for connection...')
                utime.sleep(1)
            print("Connection successfully made: " + wlan.ifconfig()[0])
            ip_address = wlan.ifconfig()[0]
            return ip_address          
        except Exception as e:
            retry_count += 1
            print("Error occurred while connecting:", e)
            if retry_count < max_retries:
                print(f"Retrying ({retry_count}/{max_retries})...")
                # Wait for a moment before retrying
                utime.sleep(1)
            else:
                print("Max retries reached. Unable to connect.")
                return "Connection failed" # Return a string if max retries are reached withut successful connection        

    return "Connection failed"


#Method to open a socket
def Open_Socket(ip):
    port = 80
    address = (ip, port)
    conn = socket.socket()

    max_retries = 3
    retry_delay = 1  # Delay between retry attempts in seconds
    retry_count = 0

    while retry_count < max_retries:
        try:
            conn.settimeout(10)  # Set socket timeout to 10 seconds
            conn.bind(address)
            conn.listen(5)
            print("Socket successfully opened and listening on port " + str(port))
            return conn    
        except Exception as e:
            print("An unexpected error occurred:", e)
            print(f"Retrying ({retry_count+1}/{max_retries})...")
            utime.sleep(retry_delay)
            retry_count += 1

    print("Max retry attempts reached. Unable to open socket.")
    return None


#Method which calls the method to build the webpage and then serves it.
async def Serve(conn):

    while True:
        try:
            client = conn.accept()[0]
            request = client.recv(1024)
            request = str(request)
            print(request)
            html = Webpage()
            client.send(html)
            client.close()
        except OSError as e:
            # Handle specific OSError exceptions
            if e.args[0] == 110:
                print("Connection timed out.")
            else:
                print("An OSError occurred:", e)
        except Exception as e:
            print("An error occurred:", e)
        finally:
            await uasyncio.sleep(0.4)
              
##############################Lights & Buzzer#########################################

#Methods which turn on green, yellow and red lights.
def TurnOnRedLight():
    Red.value(1)
    Yellow.value(0)
    Green.value(0)

def TurnOnYellowLight():
    Red.value(0)
    Yellow.value(1)
    Green.value(0)

def TurnOnGreenLight():
    Red.value(0)
    Yellow.value(0)
    Green.value(1)
    
def Beep():
    global Beeping, BeepingOverride
    onTime = 50
    print('Start Beeping Thread')
    while Beeping and not BeepingOverride:
        Buzzer.duty_u16(32767)
        utime.sleep_ms(onTime)
        Buzzer.duty_u16(0)
        utime.sleep_ms(1000-onTime)
    print("End Beeping Thread")

#Method which analyses sensor data and determines if it is good(green), indifferent(yellow), or bad(red). 
def CheckSensorReadings():
        
        global bme, co2eq, tvoc, Beeping

        temp_int = int(bme.values[0].split('.')[0])
        co2eq_int = int(co2eq)
        tvoc_int = int(tvoc)

        Temp_Red_low = 16
        Temp_Red_high = 24
        Temp_Yellow_low = 17
        Temp_Yellow_high = 22

        CO2_Yellow_Threshold = 600
        CO2_Red_Threshold = 1000
        
        TVOC_Yellow_Threshold = 800
        TVOC_Red_Threshold = 1200
        
        if temp_int < Temp_Red_low or temp_int > Temp_Red_high or co2eq_int > CO2_Yellow_Threshold or tvoc_int > TVOC_Yellow_Threshold:
            TurnOnRedLight()
            if Beeping == False:
                _thread.start_new_thread(Beep,())
            Beeping = True
            LogAirQualityProblems()
        elif temp_int < Temp_Yellow_low or temp_int > Temp_Yellow_high or co2eq_int > CO2_Red_Threshold or tvoc_int > TVOC_Red_Threshold:
            TurnOnYellowLight()
            Beeping = False
            BeepingOverride = False
        else:
            TurnOnGreenLight()
            Beeping = False
            BeepingOverride = False

###################################Logging################################################
            
#Method which will log the data to a .CSV file.
def LogAirQualityProblems():
    
    filename = "data.csv"
    
    with open(filename, mode='a') as csv_file:
            
        current_time = format_time()
            
        data_str = "{},{},{},{},{},{}\n".format(bme.values[0],bme.values[1],bme.values[2],co2eq,tvoc,current_time)    
        
        csv_file.write(data_str)
        
        
def format_time():
    # Get current time as a tuple (year, month, day, hour, minute, second, weekday, yearday)
    t = utime.localtime()
    # Format the time as YYYY-MM-DD HH:MM:SS
    return "{:04d}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}".format(t[0], t[1], t[2], t[3], t[4], t[5])
                    
###################################Buttons#################################################

#Turns off Buzzer after button press
def BeepingOverrideIRQHandler(pin):
    global BeepingOverride
    print(pin)
    if Beeping == True:
        print("Silence Beeping")
        BeepingOverride = True

def ChangeDisplayIRQHandler(pin):
    print(pin)
    print('Button Press 2')

#Button interrupters
ButtonOverrideBeeping.irq(trigger=machine.Pin.IRQ_RISING, handler=BeepingOverrideIRQHandler)
ButtonChangeDisplay.irq(trigger=machine.Pin.IRQ_RISING, handler=ChangeDisplayIRQHandler)

###################################Main#################################################

async def main():

    while True:
        internetProtocol = Connect()
        if internetProtocol is not None:
            connection = Open_Socket(internetProtocol)
            uasyncio.create_task(ObtainSensorReadings())
            uasyncio.create_task(Serve(connection))
        
        await uasyncio.sleep(3600)   # Keep the event loop running
     
loop = uasyncio.get_event_loop()
loop.run_until_complete(main())

##############################################################################################
