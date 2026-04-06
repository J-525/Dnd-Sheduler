from flask import Flask, render_template, request, jsonify, redirect, url_for
import csv
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import os

app = Flask(__name__)

CSV_FILE = 'DND_SCHEDULE_MAP - Sheet1.csv'
PLAYERS = ['AZIR', 'VARIS', 'ALERIA', 'SILVER', 'IGRIS', 'DUNGEON MASTER']
STATUSES = ['AVAILABLE', 'MAYBE', 'UNAVAILABLE']

class CSVManager:
    @staticmethod
    def read_csv() -> List[Dict]:
        """Read CSV and return list of dictionaries"""
        data = []
        try:
            with open(CSV_FILE, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    data.append(row)
        except Exception as e:
            print(f"Error reading CSV: {e}")
        return data
    
    @staticmethod
    def write_csv(data: List[Dict]):
        """Write data back to CSV"""
        if not data:
            return
        
        fieldnames = ['DATE', 'DAY'] + PLAYERS + ['RESULT']
        try:
            with open(CSV_FILE, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(data)
        except Exception as e:
            print(f"Error writing CSV: {e}")
    
    @staticmethod
    def get_date_row(date_str: str) -> Optional[Dict]:
        """Get row for specific date"""
        data = CSVManager.read_csv()
        for row in data:
            if row['DATE'] == date_str:
                return row
        return None
    
    @staticmethod
    def update_status(date_str: str, player: str, status: str):
        """Update player status for a date"""
        data = CSVManager.read_csv()
        updated = False
        for row in data:
            if row['DATE'] == date_str:
                row[player] = status
                row['RESULT'] = CSVManager.calculate_result(row)
                updated = True
                break
        
        if not updated:
            # Create new row if date doesn't exist
            target_date = datetime.strptime(date_str, '%d-%m-%Y')
            new_row = {
                'DATE': date_str,
                'DAY': target_date.strftime('%A'),
                'RESULT': '...'
            }
            for p in PLAYERS:
                new_row[p] = status if p == player else ''
            new_row['RESULT'] = CSVManager.calculate_result(new_row)
            data.append(new_row)
            data.sort(key=lambda x: datetime.strptime(x['DATE'], '%d-%m-%Y'))
        
        CSVManager.write_csv(data)
    
    @staticmethod
    def calculate_result(row: Dict) -> str:
        """Calculate RESULT based on player statuses using Excel formula logic"""
        # Count filled statuses (all 6 players)
        filled_count = sum(1 for player in PLAYERS if row.get(player, '').strip())
        
        # If not all 6 filled, return "..."
        if filled_count < 6:
            return '...'
        
        # If Dungeon Master unavailable, NOT SCHEDULED
        dm_status = row.get('DUNGEON MASTER', '').strip()
        if dm_status == 'UNAVAILABLE':
            return 'NOT SCHEDULED'
        
        # If any MAYBE, POTENTIALLY
        maybe_count = sum(1 for player in PLAYERS if row.get(player, '').strip() == 'MAYBE')
        if maybe_count > 0:
            return 'POTENTIALLY'
        
        # If more than 1 player (excluding DM) unavailable, NOT SCHEDULED
        players_without_dm = [p for p in PLAYERS if p != 'DUNGEON MASTER']
        unavailable_count = sum(1 for player in players_without_dm if row.get(player, '').strip() == 'UNAVAILABLE')
        if unavailable_count > 1:
            return 'NOT SCHEDULED'
        
        # Otherwise SCHEDULED
        return 'SCHEDULED'
    
    @staticmethod
    def get_next_n_days(n: int = 30) -> List[Dict]:
        """Get next N days from today"""
        today = datetime.now()
        data = CSVManager.read_csv()
        result = []
        
        for i in range(n):
            target_date = today + timedelta(days=i)
            date_str = target_date.strftime('%d-%m-%Y')
            
            found = False
            for row in data:
                if row['DATE'] == date_str:
                    result.append(row)
                    found = True
                    break
            
            if not found:
                new_row = {
                    'DATE': date_str,
                    'DAY': target_date.strftime('%A'),
                    'RESULT': '...'
                }
                for player in PLAYERS:
                    new_row[player] = ''
                result.append(new_row)
        
        return result
    
    @staticmethod
    def ensure_dates_exist(days: int = 30):
        """Ensure CSV has entries for next N days"""
        today = datetime.now()
        data = CSVManager.read_csv()
        existing_dates = {row['DATE'] for row in data}
        
        new_rows = []
        for i in range(days):
            target_date = today + timedelta(days=i)
            date_str = target_date.strftime('%d-%m-%Y')
            
            if date_str not in existing_dates:
                new_row = {
                    'DATE': date_str,
                    'DAY': target_date.strftime('%A'),
                    'RESULT': '...'
                }
                for player in PLAYERS:
                    new_row[player] = ''
                new_rows.append(new_row)
        
        if new_rows:
            data.extend(new_rows)
            data.sort(key=lambda x: datetime.strptime(x['DATE'], '%d-%m-%Y'))
            CSVManager.write_csv(data)


@app.route('/')
def index():
    """Main schedule page"""
    CSVManager.ensure_dates_exist(30)
    return render_template('index.html', players=PLAYERS)


@app.route('/api/schedule/<int:days>')
def get_schedule(days):
    """API endpoint to get schedule data"""
    days = min(max(days, 1), 60)
    schedule = CSVManager.get_next_n_days(days)
    return jsonify(schedule)


@app.route('/api/update', methods=['POST'])
def update_schedule():
    """API endpoint to update player status"""
    data = request.json
    date = data.get('date')
    player = data.get('player')
    status = data.get('status')
    
    if not all([date, player, status]):
        return jsonify({'error': 'Missing required fields'}), 400
    
    if player not in PLAYERS:
        return jsonify({'error': 'Invalid player'}), 400
    
    if status not in STATUSES and status != '':
        return jsonify({'error': 'Invalid status'}), 400
    
    try:
        CSVManager.update_status(date, player, status)
        return jsonify({'success': True, 'message': 'Status updated'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/bulk-update', methods=['POST'])
def bulk_update():
    """API endpoint to bulk update schedule"""
    data = request.json
    updates = data.get('updates', [])
    
    if not updates:
        return jsonify({'error': 'No updates provided'}), 400
    
    try:
        for update in updates:
            date = update.get('date')
            player = update.get('player')
            status = update.get('status')
            
            if all([date, player, status]):
                CSVManager.update_status(date, player, status)
        
        return jsonify({'success': True, 'message': f'{len(updates)} updates applied'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    CSVManager.ensure_dates_exist(30)
    app.run(host='0.0.0.0', port=5000, debug=True)
